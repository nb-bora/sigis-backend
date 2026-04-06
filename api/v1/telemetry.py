"""
Routes d'observabilité — /v1/telemetry
--------------------------------------
GET  /v1/telemetry/events   — liste les événements du buffer (backend + frontend)
GET  /v1/telemetry/stats    — statistiques agrégées (taux d'erreur, p95, …)
POST /v1/telemetry/events   — le frontend pousse ses propres événements
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from api.deps import RequirePermissionDep, UserId
from api.middleware.access_log import TelemetryStore
from domain.identity.permission import Permission

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

# ── Schémas ────────────────────────────────────────────────────────────────


class FrontendEventPayload(BaseModel):
    """Événement émis par le frontend."""

    kind: str = "ui"
    action: str = ""
    resource: str = ""
    path: str = ""
    method: str = ""
    status_code: int | None = None
    duration_ms: float | None = None
    request_id: str | None = None
    meta: dict[str, Any] = {}
    # Timestamp côté client (ISO 8601) ; si absent, on utilise l'heure serveur
    client_ts: str | None = None


class TelemetryEventOut(BaseModel):
    id: str
    ts: str
    kind: str
    method: str
    path: str
    status_code: int | None
    duration_ms: float | None
    user_id: str | None
    request_id: str | None
    client_ip: str
    user_agent: str
    action: str
    resource: str
    meta: dict[str, Any]


class TelemetryListOut(BaseModel):
    total: int
    items: list[TelemetryEventOut]


class TelemetryStatsOut(BaseModel):
    total_requests: int
    error_rate_pct: float
    avg_duration_ms: float
    p95_duration_ms: float
    buffer_size: int
    frontend_events: int


# ── Helpers ────────────────────────────────────────────────────────────────


def _get_store(request: Request) -> TelemetryStore:
    store: TelemetryStore | None = getattr(request.app.state, "telemetry_store", None)
    if store is None:
        raise RuntimeError("TelemetryStore non initialisé dans app.state")
    return store


# ── Routes ─────────────────────────────────────────────────────────────────


@router.get(
    "/events",
    dependencies=[Depends(RequirePermissionDep(Permission.TELEMETRY_READ))],
    response_model=TelemetryListOut,
)
async def list_events(
    request: Request,
    _user: UserId,
    kind: str | None = Query(None, description="Filtrer par kind : http | ui | api | nav | error"),
    user_id: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
) -> TelemetryListOut:
    """Retourne les N derniers événements du buffer circulaire (max 2 000)."""
    store = _get_store(request)
    items, total = store.list_events(kind=kind, user_id=user_id, skip=skip, limit=limit)
    return TelemetryListOut(total=total, items=[TelemetryEventOut(**e) for e in items])


@router.get(
    "/stats",
    dependencies=[Depends(RequirePermissionDep(Permission.TELEMETRY_READ))],
    response_model=TelemetryStatsOut,
)
async def get_stats(
    request: Request,
    _user: UserId,
) -> TelemetryStatsOut:
    """Statistiques agrégées sur le buffer courant."""
    store = _get_store(request)
    return TelemetryStatsOut(**store.stats())


@router.post(
    "/events",
    dependencies=[Depends(RequirePermissionDep(Permission.TELEMETRY_READ))],
    status_code=201,
)
async def push_frontend_events(
    request: Request,
    events: list[FrontendEventPayload],
    user_id: UserId,
) -> dict[str, int]:
    """
    Le frontend envoie un lot d'événements (UI, navigation, appels API, erreurs).
    Taille max : 100 événements par batch.
    """
    store = _get_store(request)
    uid_str = str(user_id)

    batch = events[:100]
    for ev in batch:
        client_ts: datetime | None = None
        if ev.client_ts:
            try:
                client_ts = datetime.fromisoformat(ev.client_ts)
                if client_ts.tzinfo is None:
                    client_ts = client_ts.replace(tzinfo=UTC)
            except ValueError:
                client_ts = None

        store.push_frontend(
            kind=ev.kind,
            action=ev.action,
            resource=ev.resource,
            user_id=uid_str,
            request_id=ev.request_id,
            duration_ms=ev.duration_ms,
            path=ev.path,
            method=ev.method,
            status_code=ev.status_code,
            meta=ev.meta,
            ts=client_ts,
        )

    return {"accepted": len(batch)}
