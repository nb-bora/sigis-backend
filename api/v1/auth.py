"""
Routeur d'authentification SIGIS.

Routes exposées :
  POST /auth/register               — Création de compte
  POST /auth/login                  — Connexion (retourne un JWT)
  POST /auth/change-password        — Changement de mot de passe (authentifié)
  POST /auth/request-password-reset — Demande de réinitialisation par e-mail
  POST /auth/reset-password         — Confirmation de la réinitialisation
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.deps import EmailDep, RequirePermissionDep, SettingsDep, UoW, UserId
from api.rate_limit import enforce_rate_limit
from api.v1.schemas import (
    ChangePasswordBody,
    LoginBody,
    LoginResponse,
    RegisterBody,
    RequestPasswordResetBody,
    ResetPasswordBody,
)
from application.use_cases.auth.change_password import ChangePassword, ChangePasswordCommand
from application.use_cases.auth.login import LoginCommand, LoginUser
from application.use_cases.auth.register_user import RegisterUser, RegisterUserCommand
from application.use_cases.auth.request_password_reset import (
    RequestPasswordReset,
    RequestPasswordResetCommand,
)
from application.use_cases.auth.reset_password import ResetPassword, ResetPasswordCommand
from common.http_errors import domain_error_to_http
from domain.errors import (
    AccountInactive,
    EmailAlreadyExists,
    InvalidCredentials,
    PhoneAlreadyExists,
    TokenExpiredOrInvalid,
)
from domain.identity.permission import Permission
from domain.identity.value_objects.phone_number import InvalidPhoneNumber

router = APIRouter(prefix="/auth", tags=["Authentification"])


# ── POST /auth/register ────────────────────────────────────────────────────


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RequirePermissionDep(Permission.AUTH_REGISTER_USER))],
    summary="Créer un compte utilisateur",
    description="""
**Rôle** : Crée un nouveau compte utilisateur SIGIS.

**Paramètres** :
- `email` — adresse e-mail unique (identifiant de connexion)
- `full_name` — prénom et nom complets
- `phone_number` — numéro camerounais valide (mobile ou fixe, format national ou +237)
- `password` — mot de passe (8 caractères minimum)
- `role` — rôle unique à attribuer (défaut : `INSPECTOR`)

**Workflow** :
1. Validation du numéro de téléphone selon le PNN ART 2014 (9 chiffres)
2. Vérification de l'unicité de l'e-mail et du numéro
3. Hachage bcrypt du mot de passe
4. Création du compte en base de données
5. Envoi d'un e-mail de bienvenue

**Alternatives** :
- `422` — numéro de téléphone invalide ou champ manquant

**Exceptions** :
- `409` — e-mail ou numéro déjà utilisé
""",
)
async def register(
    body: RegisterBody,
    uow: UoW,
    email_svc: EmailDep,
) -> dict:
    uc = RegisterUser(uow, email_svc)
    try:
        result = await uc.execute(
            RegisterUserCommand(
                email=body.email,
                full_name=body.full_name,
                phone_number=body.phone_number,
                password=body.password,
                role=body.role,
            )
        )
    except InvalidPhoneNumber as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    except (EmailAlreadyExists, PhoneAlreadyExists) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return {"user_id": str(result.user_id)}


# ── POST /auth/login ───────────────────────────────────────────────────────


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Connexion — obtenir un JWT d'accès",
    description="""
**Rôle** : Authentifie un utilisateur et retourne un JSON Web Token (JWT) d'accès.

**Paramètres** :
- `email` — adresse e-mail du compte
- `password` — mot de passe

**Workflow** :
1. Recherche du compte par e-mail
2. Vérification du mot de passe (bcrypt)
3. Vérification que le compte est actif
4. Génération d'un JWT signé avec la clé secrète (`HS256`)
   — le payload contient `sub` (user_id), `email`, `role`, `exp`

**Alternatives** :
- Utilisez le header `Authorization: Bearer <token>` sur toutes les routes protégées.
- Le token expire après `SIGIS_ACCESS_TOKEN_EXPIRE_MINUTES` (défaut : 60 min).

**Exceptions** :
- `401` — identifiants incorrects ou compte inactif
""",
)
async def login(
    request: Request,
    body: LoginBody,
    uow: UoW,
    settings: SettingsDep,
) -> LoginResponse:
    await enforce_rate_limit(
        request,
        key_prefix="login",
        max_per_minute=settings.login_rate_limit_per_minute,
    )
    uc = LoginUser(uow, settings)
    try:
        result = await uc.execute(LoginCommand(email=body.email, password=body.password))
    except (InvalidCredentials, AccountInactive) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    return LoginResponse(
        access_token=result.access_token,
        user_id=result.user_id,
        role=result.role,
    )


# ── POST /auth/change-password ─────────────────────────────────────────────


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Changer son mot de passe",
    description="""
**Rôle** : Permet à un utilisateur authentifié de modifier son mot de passe.

**Authentification** : JWT Bearer obligatoire (`Authorization: Bearer <token>`).

**Paramètres** :
- `current_password` — mot de passe actuel (vérification obligatoire)
- `new_password` — nouveau mot de passe (8 caractères minimum)

**Workflow** :
1. Identification de l'utilisateur depuis le JWT
2. Vérification du mot de passe actuel (bcrypt)
3. Hachage et mise à jour du nouveau mot de passe
4. Envoi d'un e-mail de confirmation de modification

**Exceptions** :
- `401` — JWT absent ou expiré, ou mot de passe actuel incorrect
""",
)
async def change_password(
    body: ChangePasswordBody,
    uow: UoW,
    email_svc: EmailDep,
    current_user_id: UserId,
) -> None:
    uc = ChangePassword(uow, email_svc)
    try:
        await uc.execute(
            ChangePasswordCommand(
                user_id=current_user_id,
                current_password=body.current_password,
                new_password=body.new_password,
            )
        )
    except InvalidCredentials as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except Exception as exc:
        raise domain_error_to_http(exc)


# ── POST /auth/request-password-reset ─────────────────────────────────────


@router.post(
    "/request-password-reset",
    status_code=status.HTTP_200_OK,
    summary="Demander la réinitialisation du mot de passe",
    description="""
**Rôle** : Déclenche l'envoi d'un e-mail contenant un lien de réinitialisation du mot de passe.

**Paramètres** :
- `email` — adresse e-mail du compte ciblé

**Workflow** :
1. Recherche du compte par e-mail
2. Génération d'un jeton sécurisé aléatoire (urlsafe 32 octets)
3. Stockage du hash SHA-256 du jeton en base (pas le jeton brut)
4. Envoi du lien `{FRONTEND_URL}/auth/reset-password?token=<jeton>` par e-mail

**Sécurité anti-énumération** :
La réponse est identique que l'adresse soit enregistrée ou non (200 OK).

**Alternatives** :
- Le lien expire après `SIGIS_RESET_TOKEN_EXPIRE_MINUTES` (défaut : 30 min).
""",
)
async def request_password_reset(
    body: RequestPasswordResetBody,
    uow: UoW,
    email_svc: EmailDep,
    settings: SettingsDep,
) -> dict:
    uc = RequestPasswordReset(uow, email_svc, settings)
    await uc.execute(RequestPasswordResetCommand(email=body.email))
    return {
        "detail": "Si un compte correspondant existe, un e-mail de réinitialisation a été envoyé."
    }


# ── POST /auth/reset-password ──────────────────────────────────────────────


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Confirmer la réinitialisation du mot de passe",
    description="""
**Rôle** : Valide le jeton de réinitialisation et applique le nouveau mot de passe.

**Paramètres** :
- `token` — jeton reçu dans le lien e-mail
- `new_password` — nouveau mot de passe (8 caractères minimum)

**Workflow** :
1. Calcul du hash SHA-256 du jeton
2. Vérification en base : jeton existant, non utilisé, non expiré
3. Hachage bcrypt du nouveau mot de passe et mise à jour
4. Marquage du jeton comme « utilisé » (usage unique)
5. Envoi d'un e-mail de confirmation

**Exceptions** :
- `400` — jeton invalide, déjà utilisé ou expiré
""",
)
async def reset_password(
    body: ResetPasswordBody,
    uow: UoW,
    email_svc: EmailDep,
) -> None:
    uc = ResetPassword(uow, email_svc)
    try:
        await uc.execute(ResetPasswordCommand(token=body.token, new_password=body.new_password))
    except TokenExpiredOrInvalid as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
