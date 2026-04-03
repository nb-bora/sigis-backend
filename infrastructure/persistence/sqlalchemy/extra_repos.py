from datetime import datetime, timezone as tz
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.exception_request.exception_request import ExceptionRequest
from domain.presence.models import CoPresenceEvent, PresenceProof
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
                created_at=datetime.now(tz.utc),
                response_body=response_body,
            )
        )
