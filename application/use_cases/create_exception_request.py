"""Signalement terrain (mini-workflow V1)."""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from domain.exception_request.exception_request import ExceptionRequest, ExceptionRequestStatus
from domain.errors import NotFound
from infrastructure.persistence.sqlalchemy.uow import SqlAlchemyUnitOfWork


@dataclass(frozen=True)
class CreateExceptionCommand:
    mission_id: UUID
    author_user_id: UUID
    message: str


class CreateExceptionRequest:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, cmd: CreateExceptionCommand) -> dict[str, object]:
        assert self._uow.missions is not None
        assert self._uow.exception_requests is not None

        mission = await self._uow.missions.get_by_id(cmd.mission_id)
        if mission is None:
            raise NotFound("Mission introuvable.")

        req = ExceptionRequest(
            id=uuid4(),
            mission_id=cmd.mission_id,
            author_user_id=cmd.author_user_id,
            created_at=datetime.now(timezone.utc),
            status=ExceptionRequestStatus.NEW,
            message=cmd.message[:4000],
        )
        await self._uow.exception_requests.add(req)
        return {"exception_request_id": str(req.id), "status": req.status.value}
