"""
Routeur de gestion des utilisateurs SIGIS.

Routes exposées :
  GET   /users         — Lister tous les utilisateurs (SUPER_ADMIN, NATIONAL_ADMIN)
  GET   /users/{id}    — Détail d'un utilisateur
  PATCH /users/{id}    — Modifier un utilisateur
  PATCH /users/{id}/roles — Mettre à jour le rôle uniquement
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.deps import RequirePermissionDep, UoW, UserId, UserRole
from api.v1.schemas import UpdateUserBody, UpdateUserRoleBody, UserResponse
from common.pagination import Page, PageParams
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
        role=u.role.value,
        is_active=u.is_active,
        created_at=u.created_at.isoformat() if u.created_at else "",
    )


# ── GET /users ─────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=Page[UserResponse],
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
async def list_users(
    uow: UoW,
    pagination: PageParams = Depends(),
    q: str | None = Query(
        None,
        description="Recherche insensible à la casse sur le nom, l’e-mail ou le téléphone.",
    ),
    role: Role | None = Query(None, description="Filtrer par rôle SIGIS."),
    is_active: bool | None = Query(None, description="Filtrer par statut du compte (actif / inactif)."),
) -> Page[UserResponse]:
    users, total = await uow.users.list_page(
        pagination.skip,
        pagination.limit,
        q=q,
        role=role,
        is_active=is_active,
    )
    return Page(
        items=[_user_to_response(u) for u in users],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


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
    user_id: UUID, uow: UoW, current_user: UserId, user_role: UserRole
) -> UserResponse:
    is_admin = user_role is not None and user_role in _ADMIN_ROLES
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
- `role` _(optionnel)_ — nouveau rôle unique (**admin seulement**)

**Accès** :
- Tout utilisateur authentifié peut modifier `full_name` et `phone_number` de **son propre** compte.
- `is_active` et `role` sont réservés aux `SUPER_ADMIN` / `NATIONAL_ADMIN`.

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
    user_role: UserRole,
) -> UserResponse:
    is_admin = user_role is not None and user_role in _ADMIN_ROLES

    if current_user != user_id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Modification réservée à votre propre profil ou aux administrateurs.",
        )
    if (body.is_active is not None or body.role is not None) and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Les champs 'is_active' et 'role' sont réservés aux administrateurs.",
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

    if body.role is not None:
        user.role = body.role

    await uow.users.update(user)
    updated = await uow.users.get_by_id(user_id)
    return _user_to_response(updated)


# ── PATCH /users/{id}/roles ────────────────────────────────────────────────


@router.patch(
    "/{user_id}/roles",
    response_model=UserResponse,
    dependencies=[Depends(RequirePermissionDep(Perm.USER_MANAGE_ROLES))],
    summary="Mettre à jour le rôle d'un utilisateur",
    description="""
**Rôle** : Définit le rôle unique de l'utilisateur.

**Accès** : `SUPER_ADMIN` ou `NATIONAL_ADMIN` uniquement.

**Paramètres** :
- `user_id` — identifiant UUID de l'utilisateur
- `role` — nouveau rôle (remplace l'ancien)

**Workflow** :
1. Vérification du rôle administrateur depuis le JWT
2. Récupération de l'utilisateur
3. Mise à jour du rôle en base
4. Retour du profil mis à jour

**Exceptions** :
- `401` — non authentifié
- `403` — rôle insuffisant
- `404` — utilisateur introuvable
""",
)
async def update_roles(
    user_id: UUID,
    body: UpdateUserRoleBody,
    uow: UoW,
) -> UserResponse:
    try:
        user = await uow.users.get_by_id(user_id)
    except NotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    user.role = body.role
    await uow.users.update(user)
    updated = await uow.users.get_by_id(user_id)
    return _user_to_response(updated)
