from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.sqlalchemy.models import UserModel


class UserRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ensure_exists(self, user_id: UUID) -> None:
        row = await self._session.get(UserModel, user_id)
        if row is None:
            self._session.add(UserModel(id=user_id, email=None))
