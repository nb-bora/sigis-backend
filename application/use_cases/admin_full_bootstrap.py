"""
Initialisation complète : schéma utilisateur, matrice RBAC (rôles × permissions), comptes démo.

Idempotent : répéter l’appel complète uniquement ce qui manque.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine

from application.use_cases.admin_seed_demo_users import SeedAccountResult, execute_seed_demo_users
from domain.identity.permission import Permission
from domain.identity.role import Role
from domain.identity.role_defaults import all_default_permissions
from infrastructure.persistence.sqlalchemy.schema_sync import (
    ensure_users_role_column,
    migrate_user_roles_table,
)
from infrastructure.persistence.sqlalchemy.uow import SqlAlchemyUnitOfWork


@dataclass(frozen=True)
class FullBootstrapResult:
    rbac_defaults_rows_inserted: int
    rbac_catalog_rows_inserted: int
    roles: list[str]
    permission_catalog_size: int
    default_password: str
    accounts: list[SeedAccountResult]


async def execute_full_bootstrap(
    *,
    engine: AsyncEngine,
    uow: SqlAlchemyUnitOfWork,
) -> FullBootstrapResult:
    """
    1. Aligner le schéma ``users`` (colonne ``role``, migration legacy ``user_roles``).
    2. Insérer les couples (rôle, permission) par défaut + compléter le catalogue ``Permission``.
    3. Créer les utilisateurs démo (un par rôle), idempotent.
    """
    async with engine.begin() as conn:
        await conn.run_sync(ensure_users_role_column)
    async with engine.begin() as conn:
        await conn.run_sync(migrate_user_roles_table)

    assert uow.role_permissions is not None
    defaults_inserted = await uow.role_permissions.seed_defaults(all_default_permissions())
    catalog_inserted = await uow.role_permissions.ensure_catalog_permissions_present()

    accounts, pwd = await execute_seed_demo_users(uow)

    return FullBootstrapResult(
        rbac_defaults_rows_inserted=defaults_inserted,
        rbac_catalog_rows_inserted=catalog_inserted,
        roles=[r.value for r in Role],
        permission_catalog_size=len(Permission),
        default_password=pwd,
        accounts=accounts,
    )
