"""Modes B (QR) et C (SMS) — invariants légers V1 (jeton + fenêtre mission)."""

from datetime import datetime, timezone
from uuid import UUID

from domain.errors import CoPresenceRejected


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def assert_qr_token_valid(
    provided_token: UUID,
    mission_host_token: UUID,
    now: datetime,
    window_start: datetime,
    window_end: datetime,
) -> None:
    if provided_token != mission_host_token:
        raise CoPresenceRejected("Jeton QR invalide.", code="INVALID_QR_TOKEN")
    nw, ws, we = _aware(now), _aware(window_start), _aware(window_end)
    if not (ws <= nw <= we):
        raise CoPresenceRejected("Mission hors fenêtre pour validation QR.", code="MISSION_EXPIRED")


def assert_sms_code_valid(
    provided_code: str,
    mission_sms_code: str | None,
    now: datetime,
    window_start: datetime,
    window_end: datetime,
) -> None:
    if not mission_sms_code:
        raise CoPresenceRejected("Code SMS non configuré pour cette mission.", code="SMS_NOT_CONFIGURED")
    if provided_code.strip() != mission_sms_code.strip():
        raise CoPresenceRejected("Code SMS invalide.", code="INVALID_SMS_CODE")
    nw, ws, we = _aware(now), _aware(window_start), _aware(window_end)
    if not (ws <= nw <= we):
        raise CoPresenceRejected("Mission hors fenêtre pour validation SMS.", code="MISSION_EXPIRED")
