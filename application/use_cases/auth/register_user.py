"""Use case : création d'un compte utilisateur."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from passlib.context import CryptContext

from domain.errors import EmailAlreadyExists, PhoneAlreadyExists
from domain.identity.role import Role
from domain.identity.user import User
from domain.identity.value_objects.phone_number import CameroonPhoneNumber
from infrastructure.email.email_service import EmailService
from infrastructure.persistence.sqlalchemy.uow import SqlAlchemyUnitOfWork

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass
class RegisterUserCommand:
    email: str
    full_name: str
    phone_number: str  # accepte tout format; validé dans le use case
    password: str
    roles: list[Role]


@dataclass
class RegisterUserResult:
    user_id: uuid.UUID


class RegisterUser:
    """
    Crée un nouveau compte utilisateur.

    Contrôles :
    - e-mail unique (EmailAlreadyExists)
    - numéro de téléphone camerounais valide + unique (InvalidPhoneNumber | PhoneAlreadyExists)
    - hachage bcrypt du mot de passe
    - envoi d'un e-mail de bienvenue
    """

    def __init__(
        self,
        uow: SqlAlchemyUnitOfWork,
        email_service: EmailService,
    ) -> None:
        self._uow = uow
        self._email_service = email_service

    async def execute(self, cmd: RegisterUserCommand) -> RegisterUserResult:
        # Valide le numéro de téléphone (lève InvalidPhoneNumber si invalide)
        phone_vo = CameroonPhoneNumber(cmd.phone_number)

        async with self._uow:
            # Unicité e-mail
            existing = await self._uow.users.get_by_email(cmd.email)
            if existing is not None:
                raise EmailAlreadyExists(f"L'adresse e-mail « {cmd.email} » est déjà utilisée.")
            # Unicité téléphone
            existing_phone = await self._uow.users.get_by_phone(phone_vo.e164)
            if existing_phone is not None:
                raise PhoneAlreadyExists(
                    f"Le numéro « {phone_vo.e164} » est déjà associé à un compte."
                )

            now = datetime.now(UTC)
            user = User(
                id=uuid.uuid4(),
                email=cmd.email.lower(),
                full_name=cmd.full_name,
                phone_number=phone_vo.e164,
                hashed_password=_pwd_ctx.hash(cmd.password),
                roles=cmd.roles,
                is_active=True,
                created_at=now,
            )
            await self._uow.users.create(user)

        # Envoi du mail de bienvenue (hors transaction)
        await self._email_service.send_welcome(
            to_email=user.email,
            full_name=user.full_name,
            roles=[r.value for r in user.roles],
        )
        return RegisterUserResult(user_id=user.id)
