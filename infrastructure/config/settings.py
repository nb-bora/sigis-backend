from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEFAULT_KEY = "CHANGE_ME_IN_PRODUCTION_USE_LONG_RANDOM_STRING"


def _backend_root() -> Path:
    """Répertoire racine du backend (répertoire contenant ``sigis.db``)."""
    return Path(__file__).resolve().parents[2]


def _default_sqlite_database_url() -> str:
    """SQLite unique du projet : ``sigis-backend/sigis.db`` (chemin absolu)."""
    return f"sqlite+aiosqlite:///{(_backend_root() / 'sigis.db').as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SIGIS_", env_file=".env", extra="ignore")

    env: str = "development"
    api_prefix: str = "/v1"
    cors_origins: str = "http://localhost:3000,https://sigis-lime.vercel.app"
    database_url: str = Field(default_factory=_default_sqlite_database_url)
    database_echo: bool = False
    # En production : mettre à false et utiliser `alembic upgrade head`
    auto_create_tables: bool = True

    # ── JWT ─────────────────────────────────────────────────────────────────
    secret_key: str = _INSECURE_DEFAULT_KEY
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    reset_token_expire_minutes: int = 30

    # ── Email (SMTP) ─────────────────────────────────────────────────────────
    # Si mail_server est vide, les e-mails sont simplement loggés (mode dev).
    mail_server: str = ""
    mail_port: int = 587
    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = "noreply@sigis.cm"
    mail_from_name: str = "SIGIS"
    mail_starttls: bool = True
    mail_ssl_tls: bool = False

    # URL du frontend pour les liens dans les e-mails
    frontend_url: str = "http://localhost:3000"

    # QR hôte : JWT court (minutes) ; 0 = désactivé côté émission (fallback UUID)
    host_qr_jwt_ttl_minutes: int = 15
    # Connexion : max tentatives par minute et par IP (0 = pas de limite)
    login_rate_limit_per_minute: int = 30

    @property
    def is_dev(self) -> bool:
        return self.env == "development"

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        if self.env == "production":
            if self.secret_key == _INSECURE_DEFAULT_KEY:
                raise ValueError(
                    "SIGIS_SECRET_KEY doit être défini avec une valeur sécurisée en production."
                )
        return self


def get_settings() -> Settings:
    return Settings()
