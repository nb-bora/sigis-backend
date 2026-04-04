"""Use case : changement de mot de passe pour un utilisateur authentifié."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from application.ports.email_port import EmailPort
from application.ports.unit_of_work import UnitOfWork
from common.password_hashing import pwd_context
from domain.errors import InvalidCredentials


@dataclass
class ChangePasswordCommand:
    user_id: uuid.UUID
    current_password: str
    new_password: str


class ChangePassword:
    """
    Permet à un utilisateur authentifié de changer son mot de passe.

    Contrôles :
    - Vérification du mot de passe actuel (InvalidCredentials si erroné)
    - Hachage bcrypt du nouveau mot de passe
    - Notification par e-mail de la modification
    """

    def __init__(self, uow: UnitOfWork, email_service: EmailPort) -> None:
        self._uow = uow
        self._email_service = email_service

    async def execute(self, cmd: ChangePasswordCommand) -> None:
        async with self._uow:
            user = await self._uow.users.get_by_id(cmd.user_id)
            if not pwd_context.verify(cmd.current_password, user.hashed_password):
                raise InvalidCredentials("Mot de passe actuel incorrect.")

            user.hashed_password = pwd_context.hash(cmd.new_password)
            await self._uow.users.update(user)

        await self._email_service.send_password_changed(
            to_email=user.email,
            full_name=user.full_name,
        )
