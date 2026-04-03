"""
Routeur de gestion des utilisateurs SIGIS.

Routes exposées :
  GET   /users         — Lister tous les utilisateurs (SUPER_ADMIN, NATIONAL_ADMIN)
  GET   /users/{id}    — Détail d'un utilisateur
  PATCH /users/{id}    — Modifier un utilisateur
  PATCH /users/{id}/roles — Mettre à jour les rôles uniquement
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import RequirePermissionDep, UoW, UserId, UserRoles
from api.v1.schemas import UpdateUserBody, UserResponse
from domain.errors import NotFound
from domain.identity.permission import Permission as Perm
from domain.identity.role import Role
from domain.identity.user import User
from domain.identity.value_objects.phone_number import CameroonPhoneNumber, InvalidPhoneNumber

_ADMIN_ROLES: frozenset[Role] = frozenset({Role.SUPER_ADMIN, Role.NATIONAL_ADMIN})

router = APIRouter(prefix="/users", tags=["Utilisateurs"])


def _user_to_response(u: User) -> UserResponse:
    return UserResponse(
        id=u.id,
        email=u.email,
        full_name=u.full_name,
        phone_number=u.phone_number,
        roles=[r.value for r in u.roles],
        is_active=u.is_active,
        created_at=u.created_at.isoformat() if u.created_at else "",
    )


# ── GET /users ─────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=list[UserResponse],
    dependencies=[Depends(RequirePermissionDep(Perm.USER_LIST))],
    summary="Lister tous les utilisateurs",
    description="""
**Rôle** : Retourne la liste complète des comptes utilisateurs de la plateforme.

**Accès** : `SUPER_ADMIN` ou `NATIONAL_ADMIN` uniquement.

**Workflow** :
1. Vérification du rôle depuis le JWT
2. Récupération de tous les utilisateurs avec leurs rôles (chargement eager)

**Exceptions** :
- `401` — non authentifié
- `403` — rôle insuffisant
""",
)
async def list_users(uow: UoW) -> list[UserResponse]:
    users = await uow.users.list_all()
    return [_user_to_response(u) for u in users]


# ── GET /users/{id} ────────────────────────────────────────────────────────


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Détail d'un utilisateur",
    description="""
**Rôle** : Retourne le profil complet d'un utilisateur.

**Paramètres** :
- `user_id` — identifiant UUID de l'utilisateur

**Accès** :
- Tout utilisateur authentifié peut consulter **son propre** profil.
- `SUPER_ADMIN` et `NATIONAL_ADMIN` peuvent consulter n'importe quel profil.

**Exceptions** :
- `401` — non authentifié
- `403` — accès refusé (profil d'un autre utilisateur sans droits admin)
- `404` — utilisateur introuvable
""",
)
async def get_user(
    user_id: UUID, uow: UoW, current_user: UserId, user_roles: UserRoles
) -> UserResponse:
    is_admin = bool(_ADMIN_ROLES & user_roles)
    if current_user != user_id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé à votre propre profil ou aux administrateurs.",
        )
    try:
        user = await uow.users.get_by_id(user_id)
    except NotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return _user_to_response(user)


# ── PATCH /users/{id} ──────────────────────────────────────────────────────


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Modifier un utilisateur",
    description="""
**Rôle** : Met à jour le profil d'un utilisateur (champs optionnels).

**Paramètres** :
- `user_id` — identifiant UUID de l'utilisateur à modifier
- `full_name` _(optionnel)_ — nouveau nom complet
- `phone_number` _(optionnel)_ — nouveau numéro de téléphone camerounais
- `is_active` _(optionnel)_ — activer / désactiver le compte (**admin seulement**)
- `roles` _(optionnel)_ — remplace entièrement la liste des rôles (**admin seulement**)

**Accès** :
- Tout utilisateur authentifié peut modifier `full_name` et `phone_number` de **son propre** compte.
- `is_active` et `roles` sont réservés aux `SUPER_ADMIN` / `NATIONAL_ADMIN`.

**Exceptions** :
- `401` — non authentifié
- `403` — modification d'un autre profil ou champ admin sans droits
- `404` — utilisateur introuvable
- `409` — numéro déjà utilisé par un autre compte
- `422` — numéro de téléphone invalide
""",
)
async def update_user(
    user_id: UUID,
    body: UpdateUserBody,
    uow: UoW,
    current_user: UserId,
    user_roles: UserRoles,
) -> UserResponse:
    is_admin = bool(_ADMIN_ROLES & user_roles)

    if current_user != user_id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Modification réservée à votre propre profil ou aux administrateurs.",
        )
    if (body.is_active is not None or body.roles is not None) and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Les champs 'is_active' et 'roles' sont réservés aux administrateurs.",
        )

    try:
        user = await uow.users.get_by_id(user_id)
    except NotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    if body.full_name is not None:
        user.full_name = body.full_name

    if body.phone_number is not None:
        try:
            phone_vo = CameroonPhoneNumber(body.phone_number)
        except InvalidPhoneNumber as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
        if phone_vo.e164 != user.phone_number:
            existing = await uow.users.get_by_phone(phone_vo.e164)
            if existing is not None and existing.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Le numéro {phone_vo.e164} est déjà utilisé.",
                )
        user.phone_number = phone_vo.e164

    if body.is_active is not None:
        user.is_active = body.is_active

    if body.roles is not None:
        user.roles = body.roles

    await uow.users.update(user)
    updated = await uow.users.get_by_id(user_id)
    return _user_to_response(updated)


# ── PATCH /users/{id}/roles ────────────────────────────────────────────────


@router.patch(
    "/{user_id}/roles",
    response_model=UserResponse,
    dependencies=[Depends(RequirePermissionDep(Perm.USER_MANAGE_ROLES))],
    summary="Mettre à jour les rôles d'un utilisateur",
    description="""
**Rôle** : Remplace entièrement la liste des rôles d'un utilisateur.

**Accès** : `SUPER_ADMIN` ou `NATIONAL_ADMIN` uniquement.

**Paramètres** :
- `user_id` — identifiant UUID de l'utilisateur
- `roles` — nouvelle liste de rôles (remplace l'ancienne)

**Workflow** :
1. Vérification du rôle administrateur depuis le JWT
2. Récupération de l'utilisateur
3. Suppression des anciens rôles + ajout des nouveaux
4. Retour du profil mis à jour

**Exceptions** :
- `401` — non authentifié
- `403` — rôle insuffisant
- `404` — utilisateur introuvable
""",
)
async def update_roles(
    user_id: UUID,
    body: UpdateUserBody,
    uow: UoW,
) -> UserResponse:
    if body.roles is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Le champ 'roles' est obligatoire pour cette route.",
        )
    try:
        user = await uow.users.get_by_id(user_id)
    except NotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    user.roles = body.roles
    await uow.users.update(user)
    updated = await uow.users.get_by_id(user_id)
    return _user_to_response(updated)
