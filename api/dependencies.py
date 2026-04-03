"""Injection FastAPI — UoW, settings (à compléter quand les adapters DB existent)."""

from collections.abc import AsyncGenerator

from infrastructure.config.settings import Settings, get_settings


async def get_settings_dep() -> AsyncGenerator[Settings, None]:
    yield get_settings()
