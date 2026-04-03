"""Règles de co-présence — mode A (deux GPS) ; B/C : autres invariants (jetons) hors de ce module."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from domain.errors import CoPresenceRejected
from domain.shared.value_objects.host_validation_mode import HostValidationMode


@dataclass(frozen=True, slots=True)
class CoPresenceParams:
    max_delay: timedelta
    max_distance_meters: float
    reinforce_under_meters: float | None = None  # option < 50 m


def assert_copresence_mode_a(
    inspector_position_time: datetime,
    host_position_time: datetime,
    distance_meters: float,
    params: CoPresenceParams,
) -> None:
    """Invariant mode APP_GPS : délai + distance mutuelle."""
    if host_position_time - inspector_position_time > params.max_delay:
        raise CoPresenceRejected("Délai inspecteur → validation hôte dépassé.", code="COPRESENCE_TIMEOUT")
    if distance_meters > params.max_distance_meters:
        raise CoPresenceRejected("Distance inspecteur–hôte trop grande.", code="COPRESENCE_DISTANCE")


def copresence_applies_gps_pair(mode: HostValidationMode) -> bool:
    return mode == HostValidationMode.APP_GPS
