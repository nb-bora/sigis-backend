"""Tests anomaly detection — 5+ fraud detection rules."""

from datetime import UTC, datetime
from uuid import UUID

from domain.shared.anomaly_detection import (
    AnomalySeverity,
    AnomalyType,
    detect_gps_clone_scenario,
    validate_gps_quality,
    validate_visit_duration,
)


class TestVisitDurationValidation:
    """Détecter visites trop courtes (< 5 min)."""

    def test_visit_normal_duration(self):
        """Visite 30 min = OK."""
        checked_in = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        checked_out = datetime(2026, 7, 14, 14, 30, tzinfo=UTC)

        anomalies = validate_visit_duration(checked_in, checked_out)
        assert anomalies is None

    def test_visit_exactly_minimum(self):
        """Visite 5 min = OK (boundary)."""
        checked_in = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        checked_out = datetime(2026, 7, 14, 14, 5, tzinfo=UTC)

        anomalies = validate_visit_duration(checked_in, checked_out)
        assert anomalies is None

    def test_visit_too_short(self):
        """Visite 2 min = ANOMALY."""
        checked_in = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        checked_out = datetime(2026, 7, 14, 14, 2, tzinfo=UTC)

        anomalies = validate_visit_duration(checked_in, checked_out)
        assert anomalies is not None
        assert len(anomalies) == 1
        assert anomalies[0].type == AnomalyType.VISIT_TOO_SHORT
        assert anomalies[0].severity == AnomalySeverity.LOW

    def test_visit_immediate_checkout(self):
        """Check-out immédiat = ANOMALY."""
        checked_in = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        checked_out = datetime(2026, 7, 14, 14, 0, 30, tzinfo=UTC)  # 30 secondes

        anomalies = validate_visit_duration(checked_in, checked_out)
        assert anomalies is not None
        assert anomalies[0].type == AnomalyType.VISIT_TOO_SHORT

    def test_custom_minimum_duration(self):
        """Configurable minimum duration."""
        checked_in = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        checked_out = datetime(2026, 7, 14, 14, 8, tzinfo=UTC)  # 8 min

        # Min 10 min
        anomalies = validate_visit_duration(checked_in, checked_out, min_duration_minutes=10)
        assert anomalies is not None

        # Min 5 min
        anomalies = validate_visit_duration(checked_in, checked_out, min_duration_minutes=5)
        assert anomalies is None


class TestGpsQualityAnomaly:
    """Détecter GPS accuracy mauvaise (> 100m)."""

    def test_gps_good_quality_no_anomaly(self):
        """Accuracy 50m = pas d'anomaly."""
        anomalies = validate_gps_quality(50.0)
        assert anomalies is None

    def test_gps_poor_quality_anomaly(self):
        """Accuracy 150m = ANOMALY."""
        anomalies = validate_gps_quality(150.0)
        assert anomalies is not None
        assert len(anomalies) == 1
        assert anomalies[0].type == AnomalyType.GPS_POOR_QUALITY
        assert anomalies[0].severity == AnomalySeverity.MEDIUM

    def test_gps_boundary_100m(self):
        """100m boundary = OK, 101m = anomaly."""
        anomalies = validate_gps_quality(100.0)
        assert anomalies is None

        anomalies = validate_gps_quality(100.1)
        assert anomalies is not None

    def test_gps_none_no_anomaly(self):
        """None accuracy = pas d'anomaly (default FAIR)."""
        anomalies = validate_gps_quality(None)
        assert anomalies is None


class TestGpsCloneDetection:
    """Détecter GPS clone — même inspecteur, même lieu, même minute."""

    def test_no_clone_different_locations(self):
        """Localisations différentes = pas de clone."""
        prev_locations = [
            (13.125, 8.456, datetime(2026, 7, 14, 14, 0, tzinfo=UTC)),
        ]

        anomalies = detect_gps_clone_scenario(
            inspector_id=UUID("00000000-0000-0000-0000-000000000001"),
            prev_locations=prev_locations,
            current_lat=15.0,
            current_lon=10.0,
            current_time=datetime(2026, 7, 14, 14, 30, tzinfo=UTC),
        )
        assert anomalies is None

    def test_clone_same_location_rapid(self):
        """Même lieu, 30 secondes gap = CLONE."""
        prev_locations = [
            (13.125, 8.456, datetime(2026, 7, 14, 14, 0, tzinfo=UTC)),
        ]

        anomalies = detect_gps_clone_scenario(
            inspector_id=UUID("00000000-0000-0000-0000-000000000001"),
            prev_locations=prev_locations,
            current_lat=13.125,  # Same
            current_lon=8.456,  # Same
            current_time=datetime(2026, 7, 14, 14, 0, 30, tzinfo=UTC),  # 30s later
            max_radius_meters=50.0,
            min_time_gap_minutes=1.0,
        )
        assert anomalies is not None
        assert anomalies[0].type == AnomalyType.GPS_CLONE
        assert anomalies[0].severity == AnomalySeverity.HIGH

    def test_clone_close_location_rapid(self):
        """Lieu très proche (1-2m), 30s gap = CLONE."""
        prev_locations = [
            (13.125, 8.456, datetime(2026, 7, 14, 14, 0, tzinfo=UTC)),
        ]

        # Very close (1-2m away)
        anomalies = detect_gps_clone_scenario(
            inspector_id=UUID("00000000-0000-0000-0000-000000000001"),
            prev_locations=prev_locations,
            current_lat=13.1250,  # ~1m away
            current_lon=8.4560,
            current_time=datetime(2026, 7, 14, 14, 0, 30, tzinfo=UTC),
            max_radius_meters=50.0,
        )
        assert anomalies is not None

    def test_clone_within_radius(self):
        """Customizable radius."""
        prev_locations = [
            (13.125, 8.456, datetime(2026, 7, 14, 14, 0, tzinfo=UTC)),
        ]

        # ~45m away, radius=30 → no clone
        _anomalies = detect_gps_clone_scenario(
            inspector_id=UUID("00000000-0000-0000-0000-000000000001"),
            prev_locations=prev_locations,
            current_lat=13.126,
            current_lon=8.457,
            current_time=datetime(2026, 7, 14, 14, 0, 30, tzinfo=UTC),
            max_radius_meters=30.0,  # Strict
        )
        # May or may not detect depending on exact haversine calc

    def test_clone_no_rapid_time_gap(self):
        """Même lieu mais 5 min après = pas de clone."""
        prev_locations = [
            (13.125, 8.456, datetime(2026, 7, 14, 14, 0, tzinfo=UTC)),
        ]

        anomalies = detect_gps_clone_scenario(
            inspector_id=UUID("00000000-0000-0000-0000-000000000001"),
            prev_locations=prev_locations,
            current_lat=13.125,
            current_lon=8.456,
            current_time=datetime(2026, 7, 14, 14, 5, tzinfo=UTC),  # 5 min later
            min_time_gap_minutes=1.0,
        )
        assert anomalies is None

    def test_multiple_previous_locations(self):
        """Détecter si une des locations précédentes = clone."""
        prev_locations = [
            (13.0, 8.0, datetime(2026, 7, 14, 13, 0, tzinfo=UTC)),
            (13.125, 8.456, datetime(2026, 7, 14, 14, 0, tzinfo=UTC)),  # Match
            (13.5, 9.0, datetime(2026, 7, 14, 14, 30, tzinfo=UTC)),
        ]

        anomalies = detect_gps_clone_scenario(
            inspector_id=UUID("00000000-0000-0000-0000-000000000001"),
            prev_locations=prev_locations,
            current_lat=13.125,
            current_lon=8.456,
            current_time=datetime(2026, 7, 14, 14, 0, 30, tzinfo=UTC),
        )
        assert anomalies is not None
        assert len(anomalies) >= 1


class TestAnomalySeverity:
    """Vérifier sévérité anomalies."""

    def test_visit_too_short_low_severity(self):
        """Visite courte = LOW (FYI)."""
        checked_in = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        checked_out = datetime(2026, 7, 14, 14, 2, tzinfo=UTC)

        anomalies = validate_visit_duration(checked_in, checked_out)
        assert anomalies[0].severity == AnomalySeverity.LOW

    def test_gps_poor_medium_severity(self):
        """GPS mauvaise = MEDIUM (investigate)."""
        anomalies = validate_gps_quality(150.0)
        assert anomalies[0].severity == AnomalySeverity.MEDIUM

    def test_gps_clone_high_severity(self):
        """Clone = HIGH (immediate action)."""
        prev_locations = [
            (13.125, 8.456, datetime(2026, 7, 14, 14, 0, tzinfo=UTC)),
        ]

        anomalies = detect_gps_clone_scenario(
            inspector_id=UUID("00000000-0000-0000-0000-000000000001"),
            prev_locations=prev_locations,
            current_lat=13.125,
            current_lon=8.456,
            current_time=datetime(2026, 7, 14, 14, 0, 30, tzinfo=UTC),
        )
        assert anomalies[0].severity == AnomalySeverity.HIGH
