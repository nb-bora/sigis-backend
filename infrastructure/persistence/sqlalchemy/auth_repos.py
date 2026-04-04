"""Dépôts de persistance liés à l'authentification et aux utilisateurs."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.errors import NotFound
from domain.identity.role import Role
from domain.identity.user import User
from infrastructure.persistence.sqlalchemy.models import PasswordResetTokenModel, UserModel


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
        role=Role(m.role),
        is_active=m.is_active,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


# ── UserAuthRepository ─────────────────────────────────────────────────────


class UserAuthRepositoryImpl:
    """Opérations de persistance complètes pour les utilisateurs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User:
        stmt = select(UserModel).where(UserModel.id == user_id)
        row = (await self._session.execute(stmt)).scalars().first()
        if row is None:
            raise NotFound(f"Utilisateur {user_id} introuvable.")
        return _model_to_user(row)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserModel).where(UserModel.email == email.lower())
        row = (await self._session.execute(stmt)).scalars().first()
        return _model_to_user(row) if row else None

    async def get_by_phone(self, phone_e164: str) -> User | None:
        stmt = select(UserModel).where(UserModel.phone_number == phone_e164)
        row = (await self._session.execute(stmt)).scalars().first()
        return _model_to_user(row) if row else None

    async def list_all(self) -> list[User]:
        rows, _ = await self.list_page(0, 10_000)
        return rows

    def _users_select_filtered(
        self,
        q: str | None,
        role: Role | None,
        is_active: bool | None,
    ):
        conditions: list = []
        if q and q.strip():
            term = f"%{q.strip()}%"
            conditions.append(
                or_(
                    UserModel.email.ilike(term),
                    UserModel.full_name.ilike(term),
                    UserModel.phone_number.ilike(term),
                )
            )
        if role is not None:
            conditions.append(UserModel.role == role.value)
        if is_active is not None:
            conditions.append(UserModel.is_active == is_active)
        stmt = select(UserModel)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        return stmt

    async def list_page(
        self,
        offset: int,
        limit: int,
        *,
        q: str | None = None,
        role: Role | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[User], int]:
        filtered = self._users_select_filtered(q, role, is_active)
        count_stmt = select(func.count()).select_from(filtered.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()
        stmt = self._users_select_filtered(q, role, is_active)
        stmt = stmt.order_by(UserModel.created_at.desc()).offset(offset).limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_model_to_user(r) for r in rows], int(total)

    async def create(self, user: User) -> None:
        model = UserModel(
            id=user.id,
            email=user.email.lower(),
            full_name=user.full_name,
            phone_number=user.phone_number,
            hashed_password=user.hashed_password,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        self._session.add(model)
        await self._session.flush()

    async def update(self, user: User) -> None:
        stmt = select(UserModel).where(UserModel.id == user.id)
        row = (await self._session.execute(stmt)).scalars().first()
        if row is None:
            raise NotFound(f"Utilisateur {user.id} introuvable.")
        row.full_name = user.full_name
        row.phone_number = user.phone_number
        row.hashed_password = user.hashed_password
        row.is_active = user.is_active
        row.role = user.role.value
        row.updated_at = _utc_now()

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
