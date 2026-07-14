"""Anomaly detection — 5+ règles pour détecter fraude."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID


class AnomalyType(StrEnum):
    """Types d'anomalies détectées."""

    GPS_CLONE = "gps_clone"  # Inspector check-in same place/time 2x
    VISIT_TOO_SHORT = "visit_too_short"  # Duration < 5 min
    GPS_POOR_QUALITY = "gps_poor_quality"  # accuracy > 100m
    RAPID_CHECKINS = "rapid_checkins"  # 3+ check-ins in 1 hour
    IMPOSSIBLE_TRAVEL = "impossible_travel"  # 2 locations > 100km in < 30 min
    DEVICE_KEY_MISMATCH = "device_key_mismatch"  # Device ID but different key


class AnomalySeverity(StrEnum):
    """Sévérité anomalie."""

    LOW = "low"  # FYI
    MEDIUM = "medium"  # Investigate
    HIGH = "high"  # Immediate action


@dataclass(frozen=True)
class Anomaly:
    """Anomalie détectée."""

    id: UUID
    type: AnomalyType
    severity: AnomalySeverity
    description: str
    entity_type: str  # "site_visit" | "presence_proof"
    entity_id: UUID
    inspector_id: UUID | None = None
    detected_at: datetime | None = None

    def __post_init__(self) -> None:
        """Set detected_at si absent."""
        if self.detected_at is None:
            object.__setattr__(self, "detected_at", datetime.now(UTC))


def validate_visit_duration(
    checked_in_at: datetime,
    checked_out_at: datetime,
    min_duration_minutes: int = 5,
) -> list[Anomaly] | None:
    """Détecter si visite < 5 min."""
    duration = checked_out_at - checked_in_at
    if duration < timedelta(minutes=min_duration_minutes):
        return [
            Anomaly(
                id=UUID("00000000-0000-0000-0000-000000000001"),
                type=AnomalyType.VISIT_TOO_SHORT,
                severity=AnomalySeverity.LOW,
                description=f"Visite {duration.total_seconds() / 60:.1f} min < {min_duration_minutes} min minimum",
                entity_type="site_visit",
                entity_id=UUID("00000000-0000-0000-0000-000000000000"),
            )
        ]
    return None


def validate_gps_quality(accuracy_m: float | None) -> list[Anomaly] | None:
    """Détecter si GPS qualité mauvaise (> 100m)."""
    if accuracy_m is None or accuracy_m <= 100:
        return None

    return [
        Anomaly(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            type=AnomalyType.GPS_POOR_QUALITY,
            severity=AnomalySeverity.MEDIUM,
            description=f"GPS accuracy {accuracy_m:.1f}m > 100m (poor quality)",
            entity_type="presence_proof",
            entity_id=UUID("00000000-0000-0000-0000-000000000000"),
        )
    ]


def detect_gps_clone_scenario(
    inspector_id: UUID,
    prev_locations: list[tuple[float, float, datetime]],  # (lat, lon, time)
    current_lat: float,
    current_lon: float,
    current_time: datetime,
    max_radius_meters: float = 50.0,
    min_time_gap_minutes: float = 1.0,
) -> list[Anomaly] | None:
    """Détecter si inspecteur check-in même lieu dans timeframe court.

    Heuristique: si 2+ locations ≤ 50m et ≤ 1 min = clone potentiel.
    """
    from domain.shared.distance import haversine_m

    anomalies = []
    for prev_lat, prev_lon, prev_time in prev_locations:
        dist = haversine_m(current_lat, current_lon, prev_lat, prev_lon)
        time_gap = (current_time - prev_time).total_seconds() / 60

        if dist <= max_radius_meters and time_gap <= min_time_gap_minutes:
            anomalies.append(
                Anomaly(
                    id=UUID("00000000-0000-0000-0000-000000000003"),
                    type=AnomalyType.GPS_CLONE,
                    severity=AnomalySeverity.HIGH,
                    description=f"Check-in same location {dist:.0f}m apart, {time_gap:.1f}min gap",
                    entity_type="presence_proof",
                    entity_id=UUID("00000000-0000-0000-0000-000000000000"),
                    inspector_id=inspector_id,
                )
            )

    return anomalies if anomalies else None
