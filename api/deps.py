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


def _extract_role_from_payload(payload: dict) -> Role | None:
    """Un seul rôle par utilisateur ; accepte l'ancienne clé JWT ``roles`` (1er élément)."""
    raw = payload.get("role")
    if raw and isinstance(raw, str) and raw in Role._value2member_map_:
        return Role(raw)
    legacy = payload.get("roles")
    if isinstance(legacy, list) and legacy:
        try:
            return Role(legacy[0])
        except ValueError:
            pass
    return None


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
    2. Récupère le rôle unique de l'utilisateur (clé JWT ``role`` ou ancienne ``roles``)
    3. Interroge la table ``role_permissions`` pour obtenir les permissions
       effectives de ce rôle
    4. Vérifie que la permission requise est présente

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
        role = _extract_role_from_payload(payload)
        roles = [role] if role is not None else []

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
        ur = _extract_role_from_payload(payload)
        if ur is None or ur not in self._required:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Droits insuffisants pour cette opération.",
            )


# ── CurrentUserRoleDep ──────────────────────────────────────────────────────


class CurrentUserRoleDep:
    """Rôle unique (JWT) ; ``None`` si bypass dev ``X-User-Id`` sans JWT."""

    async def __call__(
        self,
        settings: Annotated[Settings, Depends(get_settings_dep)],
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
        x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    ) -> Role | None:
        if credentials is not None:
            payload = _decode_token(credentials.credentials, settings)
            return _extract_role_from_payload(payload)
        if x_user_id and settings.is_dev:
            return None
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
UserRole = Annotated[Role | None, Depends(CurrentUserRoleDep())]
