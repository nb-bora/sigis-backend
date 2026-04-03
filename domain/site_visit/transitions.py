"""Transitions SiteVisit — règles pures (statuts)."""

from datetime import datetime, timezone

from domain.errors import AlreadyCheckedOut, DomainError, InvariantViolation
from domain.shared.value_objects.host_validation_mode import HostValidationMode
from domain.site_visit.site_visit import SiteVisit, SiteVisitStatus


def ensure_mission_window(now: datetime, window_start: datetime, window_end: datetime) -> None:
    ws = window_start if window_start.tzinfo else window_start.replace(tzinfo=timezone.utc)
    we = window_end if window_end.tzinfo else window_end.replace(tzinfo=timezone.utc)
    nw = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    if not (ws <= nw <= we):
        raise DomainError("Mission hors fenêtre horaire.", code="MISSION_EXPIRED")


def start_check_in(
    visit: SiteVisit,
    *,
    now: datetime,
    mode: HostValidationMode,
) -> None:
    if visit.status != SiteVisitStatus.SCHEDULED:
        raise InvariantViolation("Check-in impossible depuis cet état.")
    visit.host_validation_mode = mode
    visit.checked_in_at = now.astimezone(timezone.utc) if now.tzinfo else now.replace(tzinfo=timezone.utc)
    visit.status = SiteVisitStatus.PENDING_HOST


def mark_copresence_ok(visit: SiteVisit, *, _validated_at: datetime) -> None:
    if visit.status != SiteVisitStatus.PENDING_HOST:
        raise InvariantViolation("Co-présence invalide depuis cet état.")
    visit.status = SiteVisitStatus.COPRESENCE_OK


def check_out(visit: SiteVisit, *, now: datetime) -> None:
    if visit.status != SiteVisitStatus.COPRESENCE_OK:
        raise InvariantViolation("Check-out impossible sans co-présence validée.")
    if visit.checked_out_at is not None:
        raise AlreadyCheckedOut("Déjà check-out.")
    visit.checked_out_at = now.astimezone(timezone.utc) if now.tzinfo else now.replace(tzinfo=timezone.utc)
    visit.status = SiteVisitStatus.COMPLETED
