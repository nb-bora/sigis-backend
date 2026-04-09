import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import infrastructure.persistence.sqlalchemy.models  # noqa: F401
from api.middleware.access_log import AccessLogMiddleware, TelemetryStore
from api.middleware.request_id import RequestIdMiddleware
from api.v1.router import api_router
from common.http_errors import domain_error_to_http
from common.openapi_errors import ErrorResponse
from domain.errors import DomainError
from domain.identity.role_defaults import all_default_permissions
from infrastructure.config.settings import get_settings
from infrastructure.persistence.sqlalchemy.base import Base
from infrastructure.persistence.sqlalchemy.schema_sync import (
    ensure_users_role_column,
    migrate_user_roles_table,
)
from infrastructure.persistence.sqlalchemy.uow import SqlAlchemyUnitOfWork


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=settings.database_echo)
    if settings.auto_create_tables:
        # Dev / tests : création directe des tables (pas de migrations Alembic).
        # Production : SIGIS_AUTO_CREATE_TABLES=false → utiliser `alembic upgrade head`.
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # Bases SQLite anciennes : ``create_all`` n'ajoute pas les colonnes manquantes — aligner ``users.role``.
    # Deux transactions : si la migration ``user_roles`` échoue, la colonne ``role`` reste créée.
    async with engine.begin() as conn:
        await conn.run_sync(ensure_users_role_column)
    async with engine.begin() as conn:
        await conn.run_sync(migrate_user_roles_table)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.telemetry_store = TelemetryStore(maxlen=2000)

    # Initialise les permissions par défaut (idempotent : n'écrase pas les surcharges)
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        inserted = await uow.role_permissions.seed_defaults(all_default_permissions())
        # Sécurité : chaque permission du catalogue enum doit exister en base
        # (au moins une ligne ; en pratique SUPER_ADMIN reçoit tout au seed).
        repaired = await uow.role_permissions.ensure_catalog_permissions_present()
        if inserted or repaired:
            import logging

            log = logging.getLogger(__name__)
            if inserted:
                log.info("RBAC : %d permissions par défaut initialisées.", inserted)
            if repaired:
                log.info(
                    "RBAC : %d permissions du catalogue ajoutées (lignes manquantes).",
                    repaired,
                )

    # Nettoyage best-effort (évite la croissance infinie des clés idempotence en offline)
    # Valeur simple (open-source) : 30 jours. Pour aller plus loin, rendre configurable via Settings.
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        cutoff = datetime.now(UTC) - timedelta(days=30)
        try:
            deleted = await uow.idempotency.delete_older_than(cutoff=cutoff)
            if deleted:
                logging.getLogger(__name__).info(
                    "Cleanup idempotency: %d lignes supprimées.", deleted
                )
        except Exception:
            # Le nettoyage ne doit jamais empêcher le démarrage.
            logging.getLogger(__name__).exception("Cleanup idempotency: échec.")

    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="SIGIS API",
        description="Traçabilité missions d'inspection — V1 pilote",
        version="0.1.0",
        lifespan=lifespan,
    )

    def custom_openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes,
            description=app.description,
        )
        openapi_schema.setdefault("components", {}).setdefault("schemas", {})["ErrorResponse"] = (
            ErrorResponse.model_json_schema()
        )
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        rid = getattr(request.state, "request_id", None)
        http_exc = domain_error_to_http(exc)
        detail = http_exc.detail
        if isinstance(detail, dict):
            body = {**detail, "request_id": rid}
            return JSONResponse(status_code=http_exc.status_code, content=body)
        return JSONResponse(
            status_code=http_exc.status_code,
            content={"code": exc.code, "message": str(detail), "request_id": rid},
        )

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    _log = logging.getLogger(__name__)
    if origins:
        _log.info("CORS: origines autorisées (%d) : %s", len(origins), ", ".join(origins))
    else:
        _log.info("CORS: aucune origine explicite → allow_origins=* (credentials désactivés)")
    # CORS: allow_credentials=True est incompatible avec allow_origins=["*"].
    # Si aucune origine n'est configurée (développement sans .env), on désactive
    # les credentials pour rester conforme à la spec CORS et éviter une erreur
    # de navigateur.
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    # Ordre d'exécution (last-added = first-executed) :
    #   1. RequestIdMiddleware   → pose le request_id
    #   2. AccessLogMiddleware   → mesure la durée totale, lit le request_id
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
