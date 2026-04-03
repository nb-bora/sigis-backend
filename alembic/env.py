"""Alembic env.py — moteur async (SQLAlchemy 2) + Base SIGIS + Settings."""

import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# Importe la Base (et tous les modèles via main.py qui les importe)
import infrastructure.persistence.sqlalchemy.models  # noqa: F401
from infrastructure.persistence.sqlalchemy.base import Base
from infrastructure.config.settings import get_settings

# ---------------------------------------------------------------------------
# Configuration Alembic
# ---------------------------------------------------------------------------
config = context.config
target_metadata = Base.metadata


def _get_url() -> str:
    """Lit SIGIS_DATABASE_URL via Settings (env var > .env > défaut)."""
    return get_settings().database_url


# ---------------------------------------------------------------------------
# Migrations hors ligne (génération SQL uniquement, sans connexion)
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Migrations en ligne (connexion async réelle)
# ---------------------------------------------------------------------------
def do_run_migrations(connection):  # type: ignore[no-untyped-def]
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(_get_url(), echo=False)
    async with engine.connect() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Point d'entrée : Alembic appelle ce module directement
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
