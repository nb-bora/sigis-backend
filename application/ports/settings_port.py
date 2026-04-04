"""Port (interface) pour les paramètres d'application nécessaires aux use cases."""

from __future__ import annotations

from typing import Protocol


class AppSettings(Protocol):
    secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    reset_token_expire_minutes: int
    frontend_url: str
    host_qr_jwt_ttl_minutes: int
    login_rate_limit_per_minute: int
