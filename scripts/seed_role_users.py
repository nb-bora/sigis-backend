"""
Crée un utilisateur de démonstration par rôle SIGIS (mot de passe identique).

Usage (depuis le répertoire ``sigis-backend``)::

    python -m scripts.seed_role_users

Variables d'environnement : mêmes que l'API (``SIGIS_DATABASE_URL``, etc.).

**Sécurité** : réservé au développement / pilote — préférez l'endpoint
``POST /v1/admin/seed-demo-users`` en environnement contrôlé.
"""

from __future__ import annotations

import asyncio

from application.use_cases.admin_seed_demo_users import execute_seed_demo_users
from infrastructure.config.settings import get_settings
from infrastructure.persistence.session import create_engine, create_session_factory
from infrastructure.persistence.sqlalchemy.uow import SqlAlchemyUnitOfWork


async def main() -> None:
    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        rows, pwd = await execute_seed_demo_users(uow)

    await engine.dispose()

    for r in rows:
        print(f"[{r.status}] {r.role} — {r.email} — {r.detail}")
    print(f"\nMot de passe par défaut : {pwd}")


if __name__ == "__main__":
    asyncio.run(main())
