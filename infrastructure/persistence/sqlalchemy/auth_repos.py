"""Dépôts de persistance liés à l'authentification et aux utilisateurs."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.errors import NotFound
from domain.identity.role import Role
from domain.identity.user import User
from infrastructure.persistence.sqlalchemy.models import (
    PasswordResetTokenModel,
    UserModel,
    UserRoleModel,
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


# ── Mappers locaux ─────────────────────────────────────────────────────────


def _model_to_user(m: UserModel) -> User:
    return User(
        id=m.id,
        email=m.email,
        full_name=m.full_name,
        phone_number=m.phone_number,
        hashed_password=m.hashed_password,
        roles=[Role(r.role) for r in m.roles],
        is_active=m.is_active,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _with_roles(stmt):  # type: ignore[return]
    """Charge les rôles en même temps que l'utilisateur (évite N+1)."""
    return stmt.options(selectinload(UserModel.roles))


# ── UserAuthRepository ─────────────────────────────────────────────────────


class UserAuthRepositoryImpl:
    """Opérations de persistance complètes pour les utilisateurs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User:
        stmt = _with_roles(select(UserModel).where(UserModel.id == user_id))
        row = (await self._session.execute(stmt)).scalars().first()
        if row is None:
            raise NotFound(f"Utilisateur {user_id} introuvable.")
        return _model_to_user(row)

    async def get_by_email(self, email: str) -> User | None:
        stmt = _with_roles(select(UserModel).where(UserModel.email == email.lower()))
        row = (await self._session.execute(stmt)).scalars().first()
        return _model_to_user(row) if row else None

    async def get_by_phone(self, phone_e164: str) -> User | None:
        stmt = _with_roles(select(UserModel).where(UserModel.phone_number == phone_e164))
        row = (await self._session.execute(stmt)).scalars().first()
        return _model_to_user(row) if row else None

    async def list_all(self) -> list[User]:
        rows, _ = await self.list_page(0, 10_000)
        return rows

    async def list_page(self, offset: int, limit: int) -> tuple[list[User], int]:
        base = select(UserModel)
        total = (await self._session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        stmt = _with_roles(select(UserModel).order_by(UserModel.created_at.desc()))
        stmt = stmt.offset(offset).limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_model_to_user(r) for r in rows], int(total)

    async def create(self, user: User) -> None:
        model = UserModel(
            id=user.id,
            email=user.email.lower(),
            full_name=user.full_name,
            phone_number=user.phone_number,
            hashed_password=user.hashed_password,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        self._session.add(model)
        # flush pour obtenir l'id en base avant d'ajouter les rôles
        await self._session.flush()
        for role in user.roles:
            self._session.add(UserRoleModel(user_id=user.id, role=role.value))

    async def update(self, user: User) -> None:
        stmt = _with_roles(select(UserModel).where(UserModel.id == user.id))
        row = (await self._session.execute(stmt)).scalars().first()
        if row is None:
            raise NotFound(f"Utilisateur {user.id} introuvable.")
        row.full_name = user.full_name
        row.phone_number = user.phone_number
        row.hashed_password = user.hashed_password
        row.is_active = user.is_active
        row.updated_at = _utc_now()
        # Synchronise les rôles
        existing_roles = {r.role for r in row.roles}
        new_roles = {r.value for r in user.roles}
        for r_model in list(row.roles):
            if r_model.role not in new_roles:
                await self._session.delete(r_model)
        for role_val in new_roles - existing_roles:
            self._session.add(UserRoleModel(user_id=user.id, role=role_val))

    async def ensure_exists(self, user_id: uuid.UUID) -> None:
        """Compatibilité ascendante avec l'ancien UserRepositoryImpl."""
        row = await self._session.get(UserModel, user_id)
        if row is None:
            raise NotFound(f"Utilisateur {user_id} introuvable.")


# ── PasswordResetTokenRepository ──────────────────────────────────────────


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


class PasswordResetTokenRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id: uuid.UUID, raw_token: str, expires_at: datetime) -> None:
        model = PasswordResetTokenModel(
            id=uuid.uuid4(),
            user_id=user_id,
            token_hash=_hash_token(raw_token),
            expires_at=expires_at,
            used=False,
            created_at=_utc_now(),
        )
        self._session.add(model)

    async def get_valid(self, raw_token: str) -> PasswordResetTokenModel | None:
        """Retourne le modèle uniquement si le jeton est non-utilisé et non-expiré."""
        token_hash = _hash_token(raw_token)
        stmt = select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.token_hash == token_hash,
            PasswordResetTokenModel.used.is_(False),
            PasswordResetTokenModel.expires_at > _utc_now(),
        )
        return (await self._session.execute(stmt)).scalars().first()

    async def mark_used(self, raw_token: str) -> None:
        token_hash = _hash_token(raw_token)
        stmt = select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.token_hash == token_hash
        )
        row = (await self._session.execute(stmt)).scalars().first()
        if row:
            row.used = True
