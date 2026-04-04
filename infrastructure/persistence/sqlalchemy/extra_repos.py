from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.audit.audit_log_entry import AuditLogEntry
from domain.exception_request.exception_request import ExceptionRequest, ExceptionRequestStatus
from domain.mission.mission_outcome import MissionOutcome
from domain.presence.models import CoPresenceEvent, PresenceProof
from infrastructure.persistence.mappers import (
    audit_log_to_domain,
    exception_request_to_domain,
    mission_outcome_to_domain,
)
from infrastructure.persistence.sqlalchemy.models import (
    AuditLogModel,
    CoPresenceEventModel,
    ExceptionRequestModel,
    IdempotencyRecordModel,
    MissionOutcomeModel,
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
                assigned_to_user_id=req.assigned_to_user_id,
                internal_comment=req.internal_comment,
                sla_due_at=req.sla_due_at,
                attachment_url=req.attachment_url,
            )
        )

    async def update(self, req: ExceptionRequest) -> None:
        row = await self._session.get(ExceptionRequestModel, req.id)
        if row is None:
            return
        row.status = req.status.value
        row.message = req.message
        row.assigned_to_user_id = req.assigned_to_user_id
        row.internal_comment = req.internal_comment
        row.sla_due_at = req.sla_due_at
        row.attachment_url = req.attachment_url

    async def get_by_id(self, exception_id: UUID) -> ExceptionRequest | None:
        row = await self._session.get(ExceptionRequestModel, exception_id)
        return exception_request_to_domain(row) if row else None

    async def list_by_mission_id(self, mission_id: UUID) -> list[ExceptionRequest]:
        result = await self._session.execute(
            select(ExceptionRequestModel).where(ExceptionRequestModel.mission_id == mission_id)
        )
        return [exception_request_to_domain(r) for r in result.scalars().all()]

    async def list_all(self, status: str | None = None) -> list[ExceptionRequest]:
        rows, _ = await self.list_page(0, 10_000, status=status)
        return rows

    def _exception_select_filtered(
        self,
        *,
        status: str | None,
        mission_id: UUID | None,
        author_user_id: UUID | None,
        assigned_to_user_id: UUID | None,
        unassigned_only: bool,
        created_from: datetime | None,
        created_to: datetime | None,
        message_q: str | None,
    ):
        q = select(ExceptionRequestModel)
        if status is not None:
            q = q.where(ExceptionRequestModel.status == status)
        if mission_id is not None:
            q = q.where(ExceptionRequestModel.mission_id == mission_id)
        if author_user_id is not None:
            q = q.where(ExceptionRequestModel.author_user_id == author_user_id)
        if unassigned_only:
            q = q.where(ExceptionRequestModel.assigned_to_user_id.is_(None))
        elif assigned_to_user_id is not None:
            q = q.where(ExceptionRequestModel.assigned_to_user_id == assigned_to_user_id)
        if created_from is not None:
            q = q.where(ExceptionRequestModel.created_at >= created_from)
        if created_to is not None:
            q = q.where(ExceptionRequestModel.created_at <= created_to)
        if message_q:
            q = q.where(ExceptionRequestModel.message.ilike(f"%{message_q}%"))
        return q

    async def count_by_status(
        self,
        *,
        mission_id: UUID | None = None,
        author_user_id: UUID | None = None,
        assigned_to_user_id: UUID | None = None,
        unassigned_only: bool = False,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        message_q: str | None = None,
    ) -> dict[str, int]:
        q = select(ExceptionRequestModel.status, func.count()).select_from(ExceptionRequestModel)
        if mission_id is not None:
            q = q.where(ExceptionRequestModel.mission_id == mission_id)
        if author_user_id is not None:
            q = q.where(ExceptionRequestModel.author_user_id == author_user_id)
        if unassigned_only:
            q = q.where(ExceptionRequestModel.assigned_to_user_id.is_(None))
        elif assigned_to_user_id is not None:
            q = q.where(ExceptionRequestModel.assigned_to_user_id == assigned_to_user_id)
        if created_from is not None:
            q = q.where(ExceptionRequestModel.created_at >= created_from)
        if created_to is not None:
            q = q.where(ExceptionRequestModel.created_at <= created_to)
        if message_q:
            q = q.where(ExceptionRequestModel.message.ilike(f"%{message_q}%"))
        q = q.group_by(ExceptionRequestModel.status)
        result = await self._session.execute(q)
        return {str(row[0]): int(row[1]) for row in result.all()}

    async def list_page(
        self,
        offset: int,
        limit: int,
        *,
        status: str | None = None,
        mission_id: UUID | None = None,
        author_user_id: UUID | None = None,
        assigned_to_user_id: UUID | None = None,
        unassigned_only: bool = False,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        message_q: str | None = None,
    ) -> tuple[list[ExceptionRequest], int]:
        q = self._exception_select_filtered(
            status=status,
            mission_id=mission_id,
            author_user_id=author_user_id,
            assigned_to_user_id=assigned_to_user_id,
            unassigned_only=unassigned_only,
            created_from=created_from,
            created_to=created_to,
            message_q=message_q,
        )
        total = (
            await self._session.execute(select(func.count()).select_from(q.subquery()))
        ).scalar_one()
        q = self._exception_select_filtered(
            status=status,
            mission_id=mission_id,
            author_user_id=author_user_id,
            assigned_to_user_id=assigned_to_user_id,
            unassigned_only=unassigned_only,
            created_from=created_from,
            created_to=created_to,
            message_q=message_q,
        )
        q = q.order_by(ExceptionRequestModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(q)
        rows = [exception_request_to_domain(r) for r in result.scalars().all()]
        return rows, int(total)

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


class MissionOutcomeRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_mission_id(self, mission_id: UUID) -> MissionOutcome | None:
        q = await self._session.execute(
            select(MissionOutcomeModel).where(MissionOutcomeModel.mission_id == mission_id)
        )
        row = q.scalar_one_or_none()
        return mission_outcome_to_domain(row) if row else None

    async def save(self, outcome: MissionOutcome) -> None:
        self._session.add(
            MissionOutcomeModel(
                id=outcome.id,
                mission_id=outcome.mission_id,
                summary=outcome.summary,
                notes=outcome.notes,
                compliance_level=outcome.compliance_level,
                created_at=outcome.created_at,
                created_by_user_id=outcome.created_by_user_id,
            )
        )


class AuditLogRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        id: UUID,
        actor_user_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: str | None,
        payload_json: str | None,
        request_id: str | None,
    ) -> None:
        self._session.add(
            AuditLogModel(
                id=id,
                created_at=datetime.now(UTC),
                actor_user_id=actor_user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                payload_json=payload_json,
                request_id=request_id,
            )
        )

    def _audit_filter_stmt(
        self,
        q: str | None,
        action: str | None,
        resource_type: str | None,
        actor_user_id: UUID | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ):
        conditions: list = []
        if q and q.strip():
            term = f"%{q.strip()}%"
            conditions.append(
                or_(
                    AuditLogModel.action.ilike(term),
                    AuditLogModel.resource_type.ilike(term),
                    AuditLogModel.resource_id.ilike(term),
                    AuditLogModel.request_id.ilike(term),
                    AuditLogModel.payload_json.ilike(term),
                )
            )
        if action and action.strip():
            conditions.append(AuditLogModel.action == action.strip())
        if resource_type and resource_type.strip():
            conditions.append(AuditLogModel.resource_type == resource_type.strip())
        if actor_user_id is not None:
            conditions.append(AuditLogModel.actor_user_id == actor_user_id)
        if created_from is not None:
            conditions.append(AuditLogModel.created_at >= created_from)
        if created_to is not None:
            conditions.append(AuditLogModel.created_at <= created_to)
        stmt = select(AuditLogModel)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        return stmt

    async def list_page(
        self,
        offset: int,
        limit: int,
        *,
        q: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        actor_user_id: UUID | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[AuditLogEntry], int]:
        filtered = self._audit_filter_stmt(
            q, action, resource_type, actor_user_id, created_from, created_to
        )
        count_stmt = select(func.count()).select_from(filtered.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()
        stmt = self._audit_filter_stmt(
            q, action, resource_type, actor_user_id, created_from, created_to
        )
        stmt = stmt.order_by(AuditLogModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        rows = [audit_log_to_domain(r) for r in result.scalars().all()]
        return rows, int(total)
