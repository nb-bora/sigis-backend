"""Use case : demande de réinitialisation de mot de passe (envoi du lien par e-mail)."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from infrastructure.config.settings import Settings
from infrastructure.email.email_service import EmailService
from infrastructure.persistence.sqlalchemy.uow import SqlAlchemyUnitOfWork


@dataclass
class RequestPasswordResetCommand:
    email: str


class RequestPasswordReset:
    """
    Génère un jeton sécurisé de réinitialisation et l'envoie par e-mail.

    Principe de sécurité : que le compte existe ou non, la réponse HTTP
    est identique (200 OK) pour éviter l'énumération d'adresses e-mail.
    Le jeton brut n'est jamais stocké ; seul son hash SHA-256 est en base.
    """

    def __init__(
        self,
        uow: SqlAlchemyUnitOfWork,
        email_service: EmailService,
        settings: Settings,
    ) -> None:
        self._uow = uow
        self._email_service = email_service
        self._settings = settings

    async def execute(self, cmd: RequestPasswordResetCommand) -> None:
        async with self._uow:
            user = await self._uow.users.get_by_email(cmd.email)
            if user is None:
                # Silencieux : on ne révèle pas si l'adresse est enregistrée
                return

            raw_token = secrets.token_urlsafe(32)
            expires_at = datetime.now(UTC) + timedelta(
                minutes=self._settings.reset_token_expire_minutes
            )
            await self._uow.reset_tokens.create(
                user_id=user.id,
                raw_token=raw_token,
                expires_at=expires_at,
            )

        await self._email_service.send_password_reset(
            to_email=user.email,
            full_name=user.full_name,
            reset_token=raw_token,
        )
