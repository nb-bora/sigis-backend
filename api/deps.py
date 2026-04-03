from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request

from infrastructure.config.settings import Settings, get_settings
from infrastructure.persistence.sqlalchemy.uow import SqlAlchemyUnitOfWork


async def get_settings_dep() -> Settings:
    return get_settings()


async def get_uow(
    request: Request,
) -> AsyncGenerator[SqlAlchemyUnitOfWork, None]:
    factory = request.app.state.session_factory
    async with SqlAlchemyUnitOfWork(factory) as uow:
        yield uow


def parse_user_id(
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> UUID:
    if x_user_id:
        return UUID(x_user_id)
    return UUID("00000000-0000-0000-0000-000000000001")


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
UoW = Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)]
UserId = Annotated[UUID, Depends(parse_user_id)]
