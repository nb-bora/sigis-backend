"""
Service d'envoi d'e-mails SIGIS.

En développement (SIGIS_MAIL_SERVER vide) : les e-mails sont loggés
en console sans être envoyés.
En production : envoi SMTP asynchrone via aiosmtplib + Jinja2.
"""

from __future__ import annotations

import logging
import pathlib
from datetime import UTC, datetime

import aiosmtplib
from jinja2 import Environment, FileSystemLoader

from infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = pathlib.Path(__file__).parent / "templates"


def _make_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=True,
    )


class EmailService:
    """
    Service de notification par e-mail.

    Utilise aiosmtplib pour l'envoi asynchrone et Jinja2 pour les
    templates HTML. Les templates partagent un layout ``base.html``.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._env = _make_jinja_env()

    # ── méthodes publiques ────────────────────────────────────────────────

    async def send_welcome(self, *, to_email: str, full_name: str, roles: list[str]) -> None:
        body = self._render(
            "welcome.html",
            full_name=full_name,
            email=to_email,
            roles=roles,
            frontend_url=self._settings.frontend_url,
            year=datetime.now(UTC).year,
        )
        await self._send(
            to=to_email,
            subject=f"Bienvenue sur SIGIS, {full_name}",
            html=body,
        )

    async def send_password_reset(
        self,
        *,
        to_email: str,
        full_name: str,
        reset_token: str,
    ) -> None:
        reset_url = f"{self._settings.frontend_url}/auth/reset-password?token={reset_token}"
        body = self._render(
            "password_reset.html",
            full_name=full_name,
            email=to_email,
            reset_url=reset_url,
            expire_minutes=self._settings.reset_token_expire_minutes,
            year=datetime.now(UTC).year,
        )
        await self._send(
            to=to_email,
            subject="Réinitialisation de votre mot de passe SIGIS",
            html=body,
        )

    async def send_password_changed(self, *, to_email: str, full_name: str) -> None:
        now = datetime.now(UTC).strftime("%d/%m/%Y à %H:%M UTC")
        body = self._render(
            "password_changed.html",
            full_name=full_name,
            changed_at=now,
            frontend_url=self._settings.frontend_url,
            year=datetime.now(UTC).year,
        )
        await self._send(
            to=to_email,
            subject="Votre mot de passe SIGIS a été modifié",
            html=body,
        )

    # ── internals ─────────────────────────────────────────────────────────

    def _render(self, template_name: str, **ctx: object) -> str:
        return self._env.get_template(template_name).render(**ctx)

    async def _send(self, *, to: str, subject: str, html: str) -> None:
        if not self._settings.mail_server:
            logger.info(
                "[EMAIL DEV] To: %s | Subject: %s\n%.200s…",
                to,
                subject,
                html,
            )
            return

        message = _build_message(
            from_addr=f"{self._settings.mail_from_name} <{self._settings.mail_from}>",
            to_addr=to,
            subject=subject,
            html=html,
        )
        try:
            await aiosmtplib.send(
                message,
                hostname=self._settings.mail_server,
                port=self._settings.mail_port,
                username=self._settings.mail_username or None,
                password=self._settings.mail_password or None,
                start_tls=self._settings.mail_starttls,
                use_tls=self._settings.mail_ssl_tls,
            )
        except Exception:
            logger.exception("Échec d'envoi d'e-mail à %s (subject: %s)", to, subject)
            raise


def _build_message(
    *,
    from_addr: str,
    to_addr: str,
    subject: str,
    html: str,
) -> aiosmtplib.EmailMessage:  # type: ignore[name-defined]
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    msg = MIMEMultipart("alternative")
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html", "utf-8"))
    return msg  # type: ignore[return-value]
