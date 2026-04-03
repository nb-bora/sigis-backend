"""Validation hôte — mode A (GPS) ou B (QR) ou C (SMS)."""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from domain.errors import Conflict, NotFound
from domain.presence.models import CoPresenceEvent, PresenceProof
from domain.shared.copresence_rules import assert_copresence_mode_a
from domain.shared.distance import haversine_m
from domain.shared.fallback_validation import assert_qr_token_valid, assert_sms_code_valid
from domain.shared.value_objects.geofence_status import GeofenceStatus
from domain.shared.value_objects.host_validation_mode import HostValidationMode
from domain.site_visit.transitions import mark_copresence_ok
from application.use_cases.check_in_inspector import default_copresence_params
from infrastructure.persistence.sqlalchemy.uow import SqlAlchemyUnitOfWork


@dataclass(frozen=True)
class ConfirmHostCommand:
    site_visit_id: UUID
    mission_id: UUID
    host_user_id: UUID
    client_request_id: str
    latitude: float | None = None
    longitude: float | None = None
    qr_token: UUID | None = None
    sms_code: str | None = None


class ConfirmHostPresence:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, cmd: ConfirmHostCommand) -> dict[str, object]:
        assert self._uow.idempotency is not None
        assert self._uow.missions is not None
        assert self._uow.site_visits is not None
        assert self._uow.presence_proofs is not None
        assert self._uow.copresence_events is not None

        scope = f"confirm_host:{cmd.site_visit_id}"
        cached = await self._uow.idempotency.get_response(scope, cmd.client_request_id)
        if cached is not None:
            return json.loads(cached)

        visit = await self._uow.site_visits.get_by_id(cmd.site_visit_id)
        if visit is None:
            raise NotFound("Visite introuvable.")
        if visit.mission_id != cmd.mission_id:
            raise Conflict("Mission incohérente avec la visite.")

        mission = await self._uow.missions.get_by_id(cmd.mission_id)
        if mission is None:
            raise NotFound("Mission introuvable.")

        mode = visit.host_validation_mode
        if mode is None:
            raise Conflict("Mode de validation hôte non défini.")

        now = datetime.now(timezone.utc)

        if mode == HostValidationMode.APP_GPS:
            if cmd.latitude is None or cmd.longitude is None:
                raise Conflict("Position hôte requise (mode APP_GPS).")
            assert visit.inspector_lat is not None and visit.inspector_lon is not None
            assert visit.checked_in_at is not None
            dist = haversine_m(
                visit.inspector_lat,
                visit.inspector_lon,
                cmd.latitude,
                cmd.longitude,
            )
            assert_copresence_mode_a(
                visit.checked_in_at,
                now,
                dist,
                default_copresence_params(),
            )
            visit.host_lat = cmd.latitude
            visit.host_lon = cmd.longitude

        elif mode == HostValidationMode.QR_STATIC:
            if cmd.qr_token is None or mission.host_token is None:
                raise Conflict("Jeton QR requis.")
            assert_qr_token_valid(
                cmd.qr_token,
                mission.host_token,
                now,
                mission.window_start,
                mission.window_end,
            )

        elif mode == HostValidationMode.SMS_SHORTCODE:
            if cmd.sms_code is None:
                raise Conflict("Code SMS requis.")
            assert_sms_code_valid(
                cmd.sms_code,
                mission.sms_code,
                now,
                mission.window_start,
                mission.window_end,
            )

        mark_copresence_ok(visit, _validated_at=now)
        await self._uow.site_visits.save(visit)

        lat = cmd.latitude if cmd.latitude is not None else visit.inspector_lat
        lon = cmd.longitude if cmd.longitude is not None else visit.inspector_lon
        if lat is None or lon is None:
            raise Conflict("Position de référence manquante pour la preuve.")
        proof = PresenceProof(
            id=uuid4(),
            site_visit_id=visit.id,
            actor_user_id=cmd.host_user_id,
            recorded_at=now,
            latitude=lat,
            longitude=lon,
            geofence_status=GeofenceStatus.OK,
        )
        await self._uow.presence_proofs.add(proof)

        event = CoPresenceEvent(
            id=uuid4(),
            site_visit_id=visit.id,
            validated_at=now,
        )
        await self._uow.copresence_events.add(
            event,
            host_validation_mode=mode.value,
        )

        payload: dict[str, object] = {"status": visit.status.value, "site_visit_id": str(visit.id)}
        await self._uow.idempotency.save(scope, cmd.client_request_id, json.dumps(payload))
        return payload
