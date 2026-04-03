"""Dépendances FastAPI partagées."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from domain.identity.permission import Permission
from domain.identity.role import Role
from infrastructure.config.settings import Settings, get_settings
from infrastructure.email.email_service import EmailService
from infrastructure.persistence.sqlalchemy.uow import SqlAlchemyUnitOfWork

# ── Dépendances de base ────────────────────────────────────────────────────


async def get_settings_dep() -> Settings:
    return get_settings()


async def get_uow(
    request: Request,
) -> AsyncGenerator[SqlAlchemyUnitOfWork, None]:
    factory = request.app.state.session_factory
    async with SqlAlchemyUnitOfWork(factory) as uow:
        yield uow


async def get_email_service(
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> EmailService:
    return EmailService(settings)


# ── Authentification JWT ───────────────────────────────────────────────────

_bearer = HTTPBearer(auto_error=False)


def _decode_token(token: str, settings: Settings) -> dict:
    """Décode un JWT et lève 401 si invalide/expiré."""
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton d'accès expiré.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton d'accès invalide.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _extract_user_id(payload: dict) -> UUID:
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton invalide.")
    return UUID(sub)


def _extract_roles(payload: dict) -> list[Role]:
    result = []
    for r in payload.get("roles", []):
        try:
            result.append(Role(r))
        except ValueError:
            pass
    return result


# ── CurrentUserDep ────────────────────────────────────────────────────────


class CurrentUserDep:
    """
    Injecte l'identifiant de l'utilisateur courant depuis le JWT Bearer.

    Mode dégradé (dev uniquement) : accepte l'en-tête ``X-User-Id`` si
    aucun JWT n'est fourni, pour rester compatible avec les tests
    d'intégration. En production, toute requête sans JWT reçoit 401.
    """

    async def __call__(
        self,
        settings: Annotated[Settings, Depends(get_settings_dep)],
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
        x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    ) -> UUID:
        if credentials is not None:
            payload = _decode_token(credentials.credentials, settings)
            return _extract_user_id(payload)
        if x_user_id and settings.is_dev:
            return UUID(x_user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── RequirePermissionDep ──────────────────────────────────────────────────


class RequirePermissionDep:
    """
    Dépendance de contrôle d'accès basée sur les permissions RBAC.

    Workflow :
    1. Extrait et vérifie le JWT Bearer
    2. Récupère les rôles de l'utilisateur (depuis le payload JWT)
    3. Interroge la table ``role_permissions`` pour obtenir les permissions
       effectives de chaque rôle (prend en compte les surcharges admin)
    4. Vérifie que la permission requise est présente dans l'union des
       permissions des rôles de l'utilisateur

    Usage :
        @router.post("/...", dependencies=[Depends(RequirePermissionDep(Permission.XXX))])
    """

    def __init__(self, required: Permission) -> None:
        self._required = required

    async def __call__(
        self,
        request: Request,
        settings: Annotated[Settings, Depends(get_settings_dep)],
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
        x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    ) -> None:
        if credentials is None:
            # Bypass autorisé uniquement en développement avec X-User-Id
            if x_user_id and settings.is_dev:
                return
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentification requise.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        payload = _decode_token(credentials.credentials, settings)
        roles = _extract_roles(payload)

        # Récupère les permissions effectives depuis la base
        factory = request.app.state.session_factory
        async with SqlAlchemyUnitOfWork(factory) as uow:
            effective = await uow.role_permissions.get_effective_permissions(roles)

        if self._required not in effective:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission « {self._required.value} » requise.",
            )


# ── RequireRolesDep (rétrocompatibilité) ──────────────────────────────────


class RequireRolesDep:
    """Contrôle d'accès par rôle direct (utilisé pour les routes d'admin des rôles)."""

    def __init__(self, required: list[Role]) -> None:
        self._required = set(required)

    async def __call__(
        self,
        settings: Annotated[Settings, Depends(get_settings_dep)],
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
    ) -> None:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentification requise.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        payload = _decode_token(credentials.credentials, settings)
        user_roles = {Role(r) for r in payload.get("roles", []) if r in Role._value2member_map_}
        if not (user_roles & self._required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Droits insuffisants pour cette opération.",
            )


# ── CurrentUserRolesDep ───────────────────────────────────────────────────


class CurrentUserRolesDep:
    """Retourne l'ensemble des rôles de l'utilisateur courant depuis le JWT."""

    async def __call__(
        self,
        settings: Annotated[Settings, Depends(get_settings_dep)],
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
        x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    ) -> set[Role]:
        if credentials is not None:
            payload = _decode_token(credentials.credentials, settings)
            return set(_extract_roles(payload))
        if x_user_id and settings.is_dev:
            return set()  # bypass dev : pas de rôles → accès de base uniquement
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Aliases ────────────────────────────────────────────────────────────────

SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
UoW = Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)]
EmailDep = Annotated[EmailService, Depends(get_email_service)]
UserId = Annotated[UUID, Depends(CurrentUserDep())]
UserRoles = Annotated[set[Role], Depends(CurrentUserRolesDep())]


def parse_user_id(
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> UUID:
    """Alias rétrocompatible pour les anciens tests."""
    if x_user_id:
        return UUID(x_user_id)
    return UUID("00000000-0000-0000-0000-000000000001")
