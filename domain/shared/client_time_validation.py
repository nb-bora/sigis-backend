"""Validation fenêtre mission avec timestamps client (offline grace)."""

from datetime import UTC, datetime, timedelta

from domain.errors import DomainError


def _aware(dt: datetime) -> datetime:
    """Normaliser datetime en UTC aware."""
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def ensure_mission_window_client_time(
    captured_at_client: datetime,
    window_start: datetime,
    window_end: datetime,
) -> None:
    """Vérifier que timestamp CLIENT est dans fenêtre mission.

    Permet offline: visite faite offline à 14h, sync à 18h = OK si 14h ∈ [14h, 16h].
    Crit: fenêtre basée sur temps capture client, pas serveur.
    """
    ct = _aware(captured_at_client)
    ws = _aware(window_start)
    we = _aware(window_end)

    if not (ws <= ct <= we):
        raise DomainError(
            "Événement hors fenêtre mission (client time).",
            code="MISSION_EXPIRED_CLIENT_TIME",
        )


def ensure_mission_window_with_grace(
    captured_at_client: datetime,
    window_start: datetime,
    window_end: datetime,
    grace_before_minutes: int = 10,
    grace_after_minutes: int = 15,
) -> None:
    """Vérifier fenêtre mission avec tolérance avant/après.

    Inspecteur arrive 10 min avant, reste 15 min après = accepté.
    """
    effective_start = _aware(window_start) - timedelta(minutes=grace_before_minutes)
    effective_end = _aware(window_end) + timedelta(minutes=grace_after_minutes)

    ct = _aware(captured_at_client)

    if not (effective_start <= ct <= effective_end):
        raise DomainError(
            "Événement hors fenêtre mission (+ grâce).",
            code="MISSION_EXPIRED_WITH_GRACE",
        )
