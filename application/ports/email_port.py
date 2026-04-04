"""Port (interface) pour le service d'envoi d'e-mails."""

from __future__ import annotations

from typing import Protocol


class EmailPort(Protocol):
    async def send_welcome(self, *, to_email: str, full_name: str, roles: list[str]) -> None: ...

    async def send_password_reset(
        self, *, to_email: str, full_name: str, reset_token: str
    ) -> None: ...

    async def send_password_changed(self, *, to_email: str, full_name: str) -> None: ...
