"""Routes Mobile — sync offline-first (VNext)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from fastapi import APIRouter, Depends, Query

from api.deps import RequirePermissionDep, UoW, UserId
from api.v1.schemas import MobileBatchResponse, MobileEventIn, MobileEventResult
from domain.identity.permission import Permission
from infrastructure.persistence.sqlalchemy.models import MobileDeviceModel, MobileEventModel

router = APIRouter(prefix="/mobile", tags=["Mobile"])


@router.post(
    "/events:batch",
    dependencies=[Depends(RequirePermissionDep(Permission.VISIT_CHECKIN))],
    summary="Upload batch d'événements mobile (offline-first)",
)
async def ingest_events_batch(
    events: list[MobileEventIn],
    uow: UoW,
    user: UserId,
) -> MobileBatchResponse:
    """
    MVP: stocke les événements offline et retourne un statut par item.

    La validation cryptographique (signature Ed25519) et l'application des transitions
    métier (CHECK_IN/HOST_CONFIRM/CHECK_OUT) seront branchées progressivement.
    """
    assert uow.session is not None
    assert uow.audit_chain is not None

    now = datetime.now(UTC)
    results: list[MobileEventResult] = []
    prev_chain_hash = await uow.audit_chain.get_last_hash()

    for e in events:
        if e.actor_user_id != user:
            results.append(
                MobileEventResult(
                    event_id=e.event_id,
                    status="REJECTED",
                    reasons=["ACTOR_MISMATCH"],
                )
            )
            continue

        # Upsert device (simple).
        device = await uow.session.get(MobileDeviceModel, e.device_id)
        if device is None:
            device = MobileDeviceModel(
                id=e.device_id,
                user_id=user,
                public_key_ed25519=e.device_public_key,
                created_at=now,
                revoked_at=None,
            )
            uow.session.add(device)
        else:
            # Si la clé change, on refuse (anti-tamper simple).
            if device.public_key_ed25519 != e.device_public_key:
                results.append(
                    MobileEventResult(
                        event_id=e.event_id,
                        status="REJECTED",
                        reasons=["DEVICE_KEY_MISMATCH"],
                    )
                )
                continue

        raw_json = json.dumps(e.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))

        row = MobileEventModel(
            id=e.event_id,
            event_type=e.type,
            mission_id=e.mission_id,
            site_visit_id=e.site_visit_id,
            actor_user_id=user,
            device_id=e.device_id,
            client_request_id=e.client_request_id,
            captured_at_client=e.captured_at_client,
            received_at_server=now,
            gps_lat=e.gps.lat if e.gps else None,
            gps_lon=e.gps.lon if e.gps else None,
            gps_accuracy_m=e.gps.accuracy_m if e.gps else None,
            gps_provider=e.gps.provider if e.gps else None,
            selfie_sha256=e.selfie.sha256 if e.selfie else None,
            selfie_mime=e.selfie.mime if e.selfie else None,
            selfie_w=e.selfie.w if e.selfie else None,
            selfie_h=e.selfie.h if e.selfie else None,
            prev_event_hash=e.prev_event_hash,
            event_hash=e.event_hash,
            signature_ed25519=e.signature_ed25519,
            raw_json=raw_json,
        )
        uow.session.add(row)
        # Tamper-evident chain (MVP): hash(prev_chain_hash + event_hash)
        entry_hash = sha256(f"{prev_chain_hash or ''}:{e.event_hash}".encode()).hexdigest()
        await uow.audit_chain.append(
            created_at=now,
            resource_type="mobile_event",
            resource_id=str(e.event_id),
            entry_hash=entry_hash,
            prev_hash=prev_chain_hash,
        )
        prev_chain_hash = entry_hash
        results.append(MobileEventResult(event_id=e.event_id, status="RECEIVED"))

    cursor = now.isoformat()
    return MobileBatchResponse(cursor=cursor, results=results)


@router.get(
    "/sync",
    dependencies=[Depends(RequirePermissionDep(Permission.MISSION_READ))],
    summary="Sync mobile (delta) — missions/établissements nécessaires",
)
async def mobile_sync(
    uow: UoW,
    user: UserId,
    cursor: str | None = Query(default=None, description="Cursor opaque de sync (ISO par défaut)."),
) -> dict[str, object]:
    """
    MVP: retourne les missions de l'inspecteur (user) + établissements associés.

    Cursor: pour l'instant ISO timestamp; à faire évoluer vers un cursor opaque.
    """
    assert uow.missions is not None
    assert uow.establishments is not None

    # MVP: on ne filtre pas encore "depuis cursor" (à ajouter quand les champs updated_at sont généralisés).
    missions = await uow.missions.list_all(inspector_id=user)
    est_ids = {m.establishment_id for m in missions}
    establishments = []
    for eid in est_ids:
        est = await uow.establishments.get_by_id(eid)
        if est is not None:
            establishments.append(
                {
                    "id": str(est.id),
                    "name": est.name,
                    "center_lat": est.center_lat,
                    "center_lon": est.center_lon,
                    "radius_strict_m": est.radius_strict_m,
                    "radius_relaxed_m": est.radius_relaxed_m,
                    "territory_code": est.territory_code,
                    "establishment_type": est.establishment_type,
                }
            )

    now = datetime.now(UTC).isoformat()
    return {
        "cursor": now,
        "missions": [
            {
                "id": str(m.id),
                "establishment_id": str(m.establishment_id),
                "inspector_id": str(m.inspector_id),
                "window_start": m.window_start.isoformat(),
                "window_end": m.window_end.isoformat(),
                "status": m.status.value,
                "host_token": str(m.host_token) if m.host_token else None,
                "designated_host_user_id": str(m.designated_host_user_id)
                if m.designated_host_user_id
                else None,
            }
            for m in missions
        ],
        "establishments": establishments,
        "server_time_utc": now,
        "cursor_in": cursor,
        "sync_id": str(uuid4()),
    }
