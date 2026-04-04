"""Check-in inspecteur — géofence + création visite + preuve."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from application.ports.unit_of_work import UnitOfWork
from domain.errors import Conflict, Forbidden, GeofenceRejected, MissionApprovalRequired, NotFound
from domain.mission.mission import MissionStatus
from domain.presence.models import PresenceProof
from domain.shared.copresence_rules import CoPresenceParams
from domain.shared.distance import haversine_m
from domain.shared.geofence_rules import GeofenceParams, geofence_status
from domain.shared.value_objects.geofence_status import GeofenceStatus
from domain.shared.value_objects.host_validation_mode import HostValidationMode
from domain.site_visit.site_visit import SiteVisit, SiteVisitStatus
from domain.site_visit.transitions import ensure_mission_window, start_check_in


@dataclass(frozen=True)
class CheckInInspectorCommand:
    mission_id: UUID
    inspector_user_id: UUID
    latitude: float
    longitude: float
    client_request_id: str
    host_validation_mode: HostValidationMode


class CheckInInspector:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, cmd: CheckInInspectorCommand) -> dict[str, object]:
        assert self._uow.idempotency is not None
        assert self._uow.missions is not None
        assert self._uow.establishments is not None
        assert self._uow.site_visits is not None
        assert self._uow.presence_proofs is not None

        scope = f"check_in:{cmd.mission_id}"
        cached = await self._uow.idempotency.get_response(scope, cmd.client_request_id)
        if cached is not None:
            return json.loads(cached)

        mission = await self._uow.missions.get_by_id(cmd.mission_id)
        if mission is None:
            raise NotFound("Mission introuvable.")
        if mission.status == MissionStatus.DRAFT:
            raise MissionApprovalRequired(
                "La mission doit être validée (passage planned) avant tout check-in."
            )
        if mission.inspector_id != cmd.inspector_user_id:
            raise Forbidden("Cet inspecteur n'est pas assigné à la mission.")

        est = await self._uow.establishments.get_by_id(mission.establishment_id)
        if est is None:
            raise NotFound("Établissement introuvable.")

        now = datetime.now(UTC)
        ensure_mission_window(now, mission.window_start, mission.window_end)

        dist = haversine_m(cmd.latitude, cmd.longitude, est.center_lat, est.center_lon)
        params = GeofenceParams(
            radius_meters_strict=est.radius_strict_m,
            radius_meters_relaxed=est.radius_relaxed_m,
        )
        gf = geofence_status(dist, params)
        if gf == GeofenceStatus.REJECTED:
            raise GeofenceRejected("Position hors zone établissement.")

        visit = await self._uow.site_visits.get_by_mission_id(mission.id)
        if visit is not None and visit.status != SiteVisitStatus.SCHEDULED:
            raise Conflict("Une visite est déjà en cours pour cette mission.")

        if visit is None:
            visit = SiteVisit(id=uuid4(), mission_id=mission.id)

        start_check_in(visit, now=now, mode=cmd.host_validation_mode)
        visit.inspector_lat = cmd.latitude
        visit.inspector_lon = cmd.longitude

        await self._uow.site_visits.save(visit)

        proof = PresenceProof(
            id=uuid4(),
            site_visit_id=visit.id,
            actor_user_id=cmd.inspector_user_id,
            recorded_at=now,
            latitude=cmd.latitude,
            longitude=cmd.longitude,
            geofence_status=gf,
        )
        await self._uow.presence_proofs.add(proof)

        payload: dict[str, object] = {
            "site_visit_id": str(visit.id),
            "geofence_status": gf.value,
            "status": visit.status.value,
        }
        await self._uow.idempotency.save(scope, cmd.client_request_id, json.dumps(payload))
        return payload


# Export params helper for confirm_host (same seuils métier — à centraliser config)
def default_copresence_params() -> CoPresenceParams:
    from datetime import timedelta

    return CoPresenceParams(
        max_delay=timedelta(minutes=15),
        max_distance_meters=100.0,
        reinforce_under_meters=50.0,
    )
