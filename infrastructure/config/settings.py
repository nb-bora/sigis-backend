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


def get_settings() -> Settings:
    return Settings()
