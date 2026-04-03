from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SIGIS_", env_file=".env", extra="ignore")

    env: str = "development"
    api_prefix: str = "/v1"
    cors_origins: str = "http://localhost:3000"
    database_url: str = "sqlite+aiosqlite:///./sigis.db"
    database_echo: bool = False
    # En production : mettre à false et utiliser `alembic upgrade head`
    auto_create_tables: bool = True

    # ── JWT ─────────────────────────────────────────────────────────────────
    secret_key: str = "CHANGE_ME_IN_PRODUCTION_USE_LONG_RANDOM_STRING"
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


def get_settings() -> Settings:
    return Settings()
