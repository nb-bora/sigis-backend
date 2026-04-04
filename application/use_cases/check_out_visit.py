"""Check-out après co-présence validée."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from application.ports.unit_of_work import UnitOfWork
from domain.errors import Conflict, Forbidden, NotFound
from domain.site_visit.transitions import check_out


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


@dataclass(frozen=True)
class CheckOutCommand:
    site_visit_id: UUID
    mission_id: UUID
    inspector_user_id: UUID
    client_request_id: str


class CheckOutVisit:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, cmd: CheckOutCommand) -> dict[str, object]:
        assert self._uow.idempotency is not None
        assert self._uow.missions is not None
        assert self._uow.site_visits is not None

        scope = f"check_out:{cmd.site_visit_id}"
        cached = await self._uow.idempotency.get_response(scope, cmd.client_request_id)
        if cached is not None:
            return json.loads(cached)

        mission = await self._uow.missions.get_by_id(cmd.mission_id)
        if mission is None:
            raise NotFound("Mission introuvable.")
        if mission.inspector_id != cmd.inspector_user_id:
            raise Forbidden("Seul l'inspecteur assigné peut clôturer.")

        visit = await self._uow.site_visits.get_by_id(cmd.site_visit_id)
        if visit is None:
            raise NotFound("Visite introuvable.")
        if visit.mission_id != cmd.mission_id:
            raise Conflict("Mission incohérente.")

        now = datetime.now(UTC)
        check_out(visit, now=now)
        await self._uow.site_visits.save(visit)

        duration_s: float | None = None
        if visit.checked_in_at and visit.checked_out_at:
            cin, cout = _aware(visit.checked_in_at), _aware(visit.checked_out_at)
            duration_s = (cout - cin).total_seconds()

        payload: dict[str, object] = {
            "status": visit.status.value,
            "checked_out_at": visit.checked_out_at.isoformat() if visit.checked_out_at else None,
            "presence_duration_seconds": duration_s,
        }
        await self._uow.idempotency.save(scope, cmd.client_request_id, json.dumps(payload))
        return payload
