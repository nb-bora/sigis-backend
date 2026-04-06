"""Middleware d'accès structuré — log toutes les requêtes HTTP avec précision milliseconde."""

from __future__ import annotations

import logging
import time
import uuid
from collections import deque
from datetime import UTC, datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("sigis.access")


def _extract_user_id(request: Request) -> str | None:
    """Tente d'extraire le user_id depuis l'état de la requête (positionné par les deps JWT)."""
    return getattr(request.state, "user_id", None)


class AccessLogMiddleware(BaseHTTPMiddleware):
    """
    Enregistre chaque requête HTTP en JSON structuré :
      - timestamp ISO 8601 (UTC, précision microseconde)
      - method, path, query_string
      - status_code
      - duration_ms (précision perf_counter → sub-milliseconde)
      - user_id (si JWT déjà vérifié)
      - request_id (tracé via RequestIdMiddleware)
      - client_ip
      - user_agent
    """

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        t_start = time.perf_counter()

        # Sauvegarde des infos de la requête AVANT l'appel (le corps peut être consommé)
        method = request.method
        path = request.url.path
        query = request.url.query
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")

        try:
            response: Response = await call_next(request)
        except Exception as exc:  # noqa: BLE001
            duration_ms = round((time.perf_counter() - t_start) * 1000, 3)
            logger.error(
                "SIGIS_ACCESS",
                extra={
                    "event": "http_request",
                    "method": method,
                    "path": path,
                    "query": query,
                    "status_code": 500,
                    "duration_ms": duration_ms,
                    "user_id": _extract_user_id(request),
                    "request_id": getattr(request.state, "request_id", None),
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                    "error": str(exc),
                },
            )
            raise

        duration_ms = round((time.perf_counter() - t_start) * 1000, 3)
        status_code = response.status_code
        user_id = _extract_user_id(request)
        request_id = getattr(request.state, "request_id", None)

        level = logging.WARNING if status_code >= 400 else logging.INFO
        logger.log(
            level,
            "%s %s → %d (%.3f ms) user=%s rid=%s ip=%s",
            method,
            path,
            status_code,
            duration_ms,
            user_id or "-",
            request_id or "-",
            client_ip,
            extra={
                "event": "http_request",
                "method": method,
                "path": path,
                "query": query,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "user_id": user_id,
                "request_id": request_id,
                "client_ip": client_ip,
                "user_agent": user_agent,
            },
        )

        # Expose la durée dans la réponse pour le debugging côté client
        response.headers["X-Response-Time-Ms"] = str(duration_ms)

        # Stocke l'event dans l'état de l'application pour l'endpoint /telemetry
        store: TelemetryStore | None = getattr(request.app.state, "telemetry_store", None)
        if store is not None:
            store.push_access(
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
                user_id=user_id,
                request_id=request_id,
                client_ip=client_ip,
                user_agent=user_agent,
            )

        return response


# ---------------------------------------------------------------------------
# Mémoire circulaire des événements (ring buffer — pas de DB)
# ---------------------------------------------------------------------------


class TelemetryEvent:
    __slots__ = (
        "id",
        "ts", "kind", "method", "path", "status_code", "duration_ms",
        "user_id", "request_id", "client_ip", "user_agent",
        "action", "resource", "meta",
    )

    def __init__(
        self,
        *,
        kind: str,
        event_id: uuid.UUID | None = None,
        ts: datetime | None = None,
        method: str = "",
        path: str = "",
        status_code: int | None = None,
        duration_ms: float | None = None,
        user_id: str | None = None,
        request_id: str | None = None,
        client_ip: str = "",
        user_agent: str = "",
        action: str = "",
        resource: str = "",
        meta: dict | None = None,
    ) -> None:
        self.id = str(event_id or uuid.uuid4())
        self.ts = ts or datetime.now(UTC)
        self.kind = kind
        self.method = method
        self.path = path
        self.status_code = status_code
        self.duration_ms = duration_ms
        self.user_id = user_id
        self.request_id = request_id
        self.client_ip = client_ip
        self.user_agent = user_agent
        self.action = action
        self.resource = resource
        self.meta = meta or {}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ts": self.ts.isoformat(),
            "kind": self.kind,
            "method": self.method,
            "path": self.path,
            "status_code": self.status_code,
            "duration_ms": self.duration_ms,
            "user_id": self.user_id,
            "request_id": self.request_id,
            "client_ip": self.client_ip,
            "user_agent": self.user_agent,
            "action": self.action,
            "resource": self.resource,
            "meta": self.meta,
        }


class TelemetryStore:
    """Buffer circulaire thread-safe (GIL Python) — stocke les N derniers événements."""

    def __init__(self, maxlen: int = 2000) -> None:
        self._buf: deque[TelemetryEvent] = deque(maxlen=maxlen)

    def push_access(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        user_id: str | None,
        request_id: str | None,
        client_ip: str,
        user_agent: str,
    ) -> None:
        self._buf.append(
            TelemetryEvent(
                kind="http",
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
                user_id=user_id,
                request_id=request_id,
                client_ip=client_ip,
                user_agent=user_agent,
            )
        )

    def push_frontend(
        self,
        *,
        kind: str,
        action: str,
        resource: str,
        user_id: str | None,
        request_id: str | None,
        duration_ms: float | None,
        path: str,
        method: str,
        status_code: int | None,
        meta: dict,
        ts: datetime | None = None,
    ) -> None:
        self._buf.append(
            TelemetryEvent(
                kind=kind,
                action=action,
                resource=resource,
                user_id=user_id,
                request_id=request_id,
                duration_ms=duration_ms,
                path=path,
                method=method,
                status_code=status_code,
                meta=meta,
                ts=ts,
            )
        )

    def list_events(
        self,
        *,
        kind: str | None = None,
        user_id: str | None = None,
        skip: int = 0,
        limit: int = 200,
    ) -> tuple[list[dict], int]:
        # itération du plus récent au plus ancien
        items = list(reversed(self._buf))
        if kind:
            items = [e for e in items if e.kind == kind]
        if user_id:
            items = [e for e in items if e.user_id == user_id]
        total = len(items)
        return [e.to_dict() for e in items[skip : skip + limit]], total

    def stats(self) -> dict:
        items = list(self._buf)
        http_items = [e for e in items if e.kind == "http"]
        if not http_items:
            return {"total_requests": 0, "error_rate_pct": 0, "avg_duration_ms": 0, "p95_duration_ms": 0, "buffer_size": 0}
        errors = [e for e in http_items if e.status_code and e.status_code >= 400]
        durations = sorted([e.duration_ms for e in http_items if e.duration_ms is not None])
        p95_idx = max(0, int(len(durations) * 0.95) - 1)
        return {
            "total_requests": len(http_items),
            "error_rate_pct": round(len(errors) / len(http_items) * 100, 1) if http_items else 0,
            "avg_duration_ms": round(sum(durations) / len(durations), 2) if durations else 0,
            "p95_duration_ms": round(durations[p95_idx], 2) if durations else 0,
            "buffer_size": len(self._buf),
            "frontend_events": len([e for e in items if e.kind != "http"]),
        }
