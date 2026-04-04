"""Use case : authentification d'un utilisateur et émission du JWT."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from application.ports.settings_port import AppSettings
from application.ports.unit_of_work import UnitOfWork
from common.password_hashing import pwd_context
from domain.errors import AccountInactive, InvalidCredentials


@dataclass
class LoginCommand:
    email: str
    password: str


@dataclass
class LoginResult:
    access_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID = None  # type: ignore[assignment]
    roles: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.roles is None:
            self.roles = []


class LoginUser:
    """
    Vérifie les identifiants et retourne un JWT d'accès.

    Erreurs :
    - InvalidCredentials — e-mail inconnu ou mot de passe erroné
    - AccountInactive    — compte désactivé
    """

    def __init__(self, uow: UnitOfWork, settings: AppSettings) -> None:
        self._uow = uow
        self._settings = settings

    async def execute(self, cmd: LoginCommand) -> LoginResult:
        async with self._uow:
            user = await self._uow.users.get_by_email(cmd.email)

        if user is None or not pwd_context.verify(cmd.password, user.hashed_password):
            raise InvalidCredentials("Identifiants incorrects.")

        if not user.is_active:
            raise AccountInactive("Ce compte est désactivé.")

        expire = datetime.now(UTC) + timedelta(minutes=self._settings.access_token_expire_minutes)
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "roles": [r.value for r in user.roles],
            "exp": expire,
        }
        token = jwt.encode(
            payload,
            self._settings.secret_key,
            algorithm=self._settings.jwt_algorithm,
        )
        return LoginResult(
            access_token=token,
            user_id=user.id,
            roles=[r.value for r in user.roles],
        )
