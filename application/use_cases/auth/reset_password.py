"""Use case : confirmation de la réinitialisation de mot de passe."""

from __future__ import annotations

from dataclasses import dataclass

from passlib.context import CryptContext

from domain.errors import TokenExpiredOrInvalid
from infrastructure.email.email_service import EmailService
from infrastructure.persistence.sqlalchemy.uow import SqlAlchemyUnitOfWork

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass
class ResetPasswordCommand:
    token: str  # jeton brut reçu par e-mail
    new_password: str


class ResetPassword:
    """
    Valide le jeton de réinitialisation et applique le nouveau mot de passe.

    Contrôles :
    - Jeton existant, non utilisé, non expiré (TokenExpiredOrInvalid sinon)
    - Le jeton est marqué « utilisé » immédiatement (usage unique)
    - Notification par e-mail de la modification
    """

    def __init__(self, uow: SqlAlchemyUnitOfWork, email_service: EmailService) -> None:
        self._uow = uow
        self._email_service = email_service

    async def execute(self, cmd: ResetPasswordCommand) -> None:
        async with self._uow:
            token_record = await self._uow.reset_tokens.get_valid(cmd.token)
            if token_record is None:
                raise TokenExpiredOrInvalid("Le lien de réinitialisation est invalide ou a expiré.")

            user = await self._uow.users.get_by_id(token_record.user_id)
            user.hashed_password = _pwd_ctx.hash(cmd.new_password)
            await self._uow.users.update(user)
            await self._uow.reset_tokens.mark_used(cmd.token)

        await self._email_service.send_password_changed(
            to_email=user.email,
            full_name=user.full_name,
        )
