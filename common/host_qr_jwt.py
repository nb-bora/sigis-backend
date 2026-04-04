"""JWT court pour QR hôte (rotation, fenêtre mission)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt

from domain.errors import CoPresenceRejected
from domain.mission.mission import Mission


def create_host_qr_jwt(
    *,
    secret_key: str,
    algorithm: str,
    ttl_minutes: int,
    mission: Mission,
) -> str:
    """Émet un JWT HS256 lié à la mission et au host_token (TTL court)."""
    if mission.host_token is None:
        raise ValueError("host_token manquant pour JWT QR.")
    ttl = timedelta(minutes=ttl_minutes)
    now = datetime.now(UTC)
    exp = now + ttl
    _ws, we = mission.window_start, mission.window_end
    if we.tzinfo is None:
        we = we.replace(tzinfo=UTC)
    if exp > we:
        exp = we
    payload = {
        "sub": str(mission.id),
        "ht": str(mission.host_token),
        "typ": "host_qr",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def verify_host_qr_jwt(
    *,
    secret_key: str,
    algorithm: str,
    token: str,
    mission: Mission,
) -> None:
    """Vérifie le JWT QR vs mission courante et fenêtre horaire."""
    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[algorithm],
            options={"require": ["exp", "sub", "ht"]},
        )
    except jwt.ExpiredSignatureError:
        raise CoPresenceRejected("Jeton QR expiré.", code="INVALID_QR_TOKEN")
    except jwt.PyJWTError:
        raise CoPresenceRejected("Jeton QR invalide.", code="INVALID_QR_TOKEN")
    if payload.get("typ") != "host_qr":
        raise CoPresenceRejected("Type de jeton QR inattendu.", code="INVALID_QR_TOKEN")
    if payload.get("sub") != str(mission.id):
        raise CoPresenceRejected("Jeton QR : mission incohérente.", code="INVALID_QR_TOKEN")
    if mission.host_token is None:
        raise CoPresenceRejected("Mission sans host_token.", code="INVALID_QR_TOKEN")
    if payload.get("ht") != str(mission.host_token):
        raise CoPresenceRejected("Jeton QR : host_token incohérent.", code="INVALID_QR_TOKEN")
    nw = datetime.now(UTC)
    ws, we = mission.window_start, mission.window_end
    ws = ws if ws.tzinfo else ws.replace(tzinfo=UTC)
    we = we if we.tzinfo else we.replace(tzinfo=UTC)
    if not (ws <= nw <= we):
        raise CoPresenceRejected("Mission hors fenêtre pour validation QR.", code="MISSION_EXPIRED")
