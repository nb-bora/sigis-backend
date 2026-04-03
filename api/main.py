from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.v1.router import api_router
from domain.errors import DomainError
from infrastructure.config.settings import get_settings
from infrastructure.persistence.sqlalchemy.base import Base
import infrastructure.persistence.sqlalchemy.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=settings.database_echo)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.engine = engine
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
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

    @app.exception_handler(DomainError)
    async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
        status_code = 400
        if exc.code == "NOT_FOUND":
            status_code = 404
        elif exc.code == "FORBIDDEN":
            status_code = 403
        elif exc.code == "CONFLICT":
            status_code = 409
        body = {"code": exc.code, "message": str(exc)}
        return JSONResponse(status_code=status_code, content=body)

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
