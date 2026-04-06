"""Routes d'administration technique (hors métier terrain)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from api.deps import UoW
from application.use_cases.admin_full_bootstrap import execute_full_bootstrap
from application.use_cases.admin_seed_demo_users import execute_seed_demo_users
from infrastructure.persistence.sqlalchemy.schema_sync import (
    ensure_users_role_column,
    migrate_user_roles_table,
)

router = APIRouter(prefix="/admin", tags=["Administration"])


class SeedDemoUserItem(BaseModel):
    role: str
    email: str
    status: str = Field(description="created | skipped")
    detail: str


class SeedDemoUsersResponse(BaseModel):
    default_password: str = Field(
        description="Mot de passe initial commun aux comptes créés (inchangé si tout était déjà présent)."
    )
    accounts: list[SeedDemoUserItem]


class BootstrapFullResponse(BaseModel):
    rbac_defaults_rows_inserted: int = Field(
        description="Lignes (rôle, permission) ajoutées lors du seed des défauts."
    )
    rbac_catalog_rows_inserted: int = Field(
        description="Lignes ajoutées pour couvrir tout le catalogue ``Permission`` (souvent 0 si déjà couvert)."
    )
    roles: list[str] = Field(description="Rôles applicatifs (énumération, matrice en base).")
    permission_catalog_size: int = Field(
        description="Nombre de permissions dans le catalogue code."
    )
    default_password: str = Field(description="Mot de passe commun des comptes démo créés.")
    accounts: list[SeedDemoUserItem]


@router.post(
    "/bootstrap",
    response_model=BootstrapFullResponse,
    summary="Initialisation complète (RBAC + comptes démo)",
    description="""
Enchaîne dans l’ordre :

1. **Schéma** : colonne ``users.role``, migration depuis ``user_roles`` si besoin.
2. **RBAC** : insertion idempotente des couples (rôle, permission) par défaut pour les cinq rôles,
   puis complément du catalogue de permissions (chaque valeur ``Permission`` présente au moins une fois en base).
3. **Utilisateurs** : un compte démo par rôle (même logique que ``/seed-demo-users``).

**Idempotence** : sûr à rappeler ; ne supprime pas les surcharges RBAC existantes.

**Accès** : route **publique** — à restreindre en production.
""",
)
async def bootstrap_full(request: Request, uow: UoW) -> BootstrapFullResponse:
    engine = request.app.state.engine
    result = await execute_full_bootstrap(engine=engine, uow=uow)
    return BootstrapFullResponse(
        rbac_defaults_rows_inserted=result.rbac_defaults_rows_inserted,
        rbac_catalog_rows_inserted=result.rbac_catalog_rows_inserted,
        roles=result.roles,
        permission_catalog_size=result.permission_catalog_size,
        default_password=result.default_password,
        accounts=[
            SeedDemoUserItem(role=r.role, email=r.email, status=r.status, detail=r.detail)
            for r in result.accounts
        ],
    )


@router.post(
    "/seed-demo-users",
    response_model=SeedDemoUsersResponse,
    summary="Créer les comptes de démonstration (un par rôle)",
    description="""
Crée jusqu'à cinq utilisateurs (``SUPER_ADMIN``, ``NATIONAL_ADMIN``, …) avec le même mot de passe par défaut.

**Idempotence** : si un e-mail seed existe déjà avec le bon rôle, le compte est ignoré.
Si l'e-mail est occupé par un autre rôle, une variante ``local.1``, ``local.2``, … est essayée.
Si le numéro de téléphone est déjà utilisé, le prochain mobile valide libre est choisi.

**Accès** : route **publique** (aucun jeton requis) — à protéger en production (pare-feu, désactivation, ou réactivation d'un garde d'accès).
""",
)
async def seed_demo_users(request: Request, uow: UoW) -> SeedDemoUsersResponse:
    # Même si le démarrage n'a pas migré (ancien processus, autre fichier DB), on aligne le schéma ici.
    engine = request.app.state.engine
    async with engine.begin() as conn:
        await conn.run_sync(ensure_users_role_column)
    async with engine.begin() as conn:
        await conn.run_sync(migrate_user_roles_table)

    rows, pwd = await execute_seed_demo_users(uow)
    return SeedDemoUsersResponse(
        default_password=pwd,
        accounts=[
            SeedDemoUserItem(role=r.role, email=r.email, status=r.status, detail=r.detail)
            for r in rows
        ],
    )
