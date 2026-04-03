from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SIGIS_", env_file=".env", extra="ignore")

    env: str = "development"
    api_prefix: str = "/v1"
    cors_origins: str = "http://localhost:3000"
    # database_url: str | None = None  # décommenter avec extra db


def get_settings() -> Settings:
    return Settings()
