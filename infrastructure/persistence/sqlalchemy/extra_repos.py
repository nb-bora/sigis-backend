from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.exception_request.exception_request import ExceptionRequest, ExceptionRequestStatus
from domain.presence.models import CoPresenceEvent, PresenceProof
from infrastructure.persistence.mappers import exception_request_to_domain
from infrastructure.persistence.sqlalchemy.models import (
    CoPresenceEventModel,
    ExceptionRequestModel,
    IdempotencyRecordModel,
    PresenceProofModel,
)


class PresenceProofRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, proof: PresenceProof) -> None:
        self._session.add(
            PresenceProofModel(
                id=proof.id,
                site_visit_id=proof.site_visit_id,
                actor_user_id=proof.actor_user_id,
                recorded_at=proof.recorded_at,
                latitude=proof.latitude,
                longitude=proof.longitude,
                geofence_status=proof.geofence_status.value,
            )
        )


class CoPresenceEventRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: CoPresenceEvent, *, host_validation_mode: str) -> None:
        self._session.add(
            CoPresenceEventModel(
                id=event.id,
                site_visit_id=event.site_visit_id,
                validated_at=event.validated_at,
                host_validation_mode=host_validation_mode,
            )
        )


class ExceptionRequestRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, req: ExceptionRequest) -> None:
        self._session.add(
            ExceptionRequestModel(
                id=req.id,
                mission_id=req.mission_id,
                author_user_id=req.author_user_id,
                created_at=req.created_at,
                status=req.status.value,
                message=req.message,
            )
        )

    async def get_by_id(self, exception_id: UUID) -> ExceptionRequest | None:
        row = await self._session.get(ExceptionRequestModel, exception_id)
        return exception_request_to_domain(row) if row else None

    async def list_by_mission_id(self, mission_id: UUID) -> list[ExceptionRequest]:
        result = await self._session.execute(
            select(ExceptionRequestModel).where(ExceptionRequestModel.mission_id == mission_id)
        )
        return [exception_request_to_domain(r) for r in result.scalars().all()]

    async def list_all(self, status: str | None = None) -> list[ExceptionRequest]:
        q = select(ExceptionRequestModel)
        if status is not None:
            q = q.where(ExceptionRequestModel.status == status)
        result = await self._session.execute(q)
        return [exception_request_to_domain(r) for r in result.scalars().all()]

    async def update_status(self, exception_id: UUID, new_status: ExceptionRequestStatus) -> None:
        row = await self._session.get(ExceptionRequestModel, exception_id)
        if row is not None:
            row.status = new_status.value


class IdempotencyRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_response(self, scope: str, client_key: str) -> str | None:
        q = await self._session.execute(
            select(IdempotencyRecordModel).where(
                IdempotencyRecordModel.scope == scope,
                IdempotencyRecordModel.client_key == client_key,
            )
        )
        row = q.scalar_one_or_none()
        return row.response_body if row else None

    async def save(self, scope: str, client_key: str, response_body: str) -> None:
        self._session.add(
            IdempotencyRecordModel(
                id=uuid4(),
                scope=scope,
                client_key=client_key,
                created_at=datetime.now(UTC),
                response_body=response_body,
            )
        )
