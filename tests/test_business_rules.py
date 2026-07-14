"""Tests règles métier — toutes les invariants."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from domain.errors import (
    AlreadyCheckedOut,
    DomainError,
    InvariantViolation,
)
from domain.shared.copresence_rules import CoPresenceParams, assert_copresence_mode_a
from domain.site_visit.site_visit import SiteVisit, SiteVisitStatus
from domain.site_visit.transitions import (
    check_out,
    mark_copresence_ok,
    start_check_in,
)
from domain.shared.value_objects.host_validation_mode import HostValidationMode


class TestSiteVisitTransitions:
    """Machine d'états SiteVisit."""

    def test_start_checkin_from_scheduled(self):
        """Check-in depuis SCHEDULED → PENDING_HOST."""
        visit = SiteVisit(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            mission_id=UUID("00000000-0000-0000-0000-000000000002"),
            status=SiteVisitStatus.SCHEDULED,
        )

        now = datetime.now(UTC)
        start_check_in(visit, now=now, mode=HostValidationMode.APP_GPS)

        assert visit.status == SiteVisitStatus.PENDING_HOST
        assert visit.host_validation_mode == HostValidationMode.APP_GPS
        assert visit.checked_in_at is not None

    def test_checkin_invalid_from_checked_in(self):
        """Check-in depuis CHECKED_IN → erreur (déjà check-in)."""
        visit = SiteVisit(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            mission_id=UUID("00000000-0000-0000-0000-000000000002"),
            status=SiteVisitStatus.CHECKED_IN,
        )

        with pytest.raises(InvariantViolation):
            start_check_in(visit, now=datetime.now(UTC), mode=HostValidationMode.APP_GPS)

    def test_mark_copresence_ok(self):
        """Marquer co-présence OK depuis PENDING_HOST → COPRESENCE_OK."""
        visit = SiteVisit(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            mission_id=UUID("00000000-0000-0000-0000-000000000002"),
            status=SiteVisitStatus.PENDING_HOST,
        )

        mark_copresence_ok(visit, _validated_at=datetime.now(UTC))

        assert visit.status == SiteVisitStatus.COPRESENCE_OK

    def test_mark_copresence_invalid_from_scheduled(self):
        """Co-présence depuis SCHEDULED → erreur."""
        visit = SiteVisit(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            mission_id=UUID("00000000-0000-0000-0000-000000000002"),
            status=SiteVisitStatus.SCHEDULED,
        )

        with pytest.raises(InvariantViolation):
            mark_copresence_ok(visit, _validated_at=datetime.now(UTC))

    def test_checkout_from_copresence_ok(self):
        """Check-out depuis COPRESENCE_OK → COMPLETED."""
        visit = SiteVisit(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            mission_id=UUID("00000000-0000-0000-0000-000000000002"),
            status=SiteVisitStatus.COPRESENCE_OK,
            checked_in_at=datetime(2026, 7, 14, 14, 0, tzinfo=UTC),
        )

        now = datetime(2026, 7, 14, 14, 30, tzinfo=UTC)
        check_out(visit, now=now)

        assert visit.status == SiteVisitStatus.COMPLETED
        assert visit.checked_out_at is not None

    def test_checkout_invalid_from_pending_host(self):
        """Check-out depuis PENDING_HOST (sans co-présence) → erreur."""
        visit = SiteVisit(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            mission_id=UUID("00000000-0000-0000-0000-000000000002"),
            status=SiteVisitStatus.PENDING_HOST,
        )

        with pytest.raises(InvariantViolation):
            check_out(visit, now=datetime.now(UTC))

    def test_double_checkout_error(self):
        """Check-out deux fois → erreur."""
        visit = SiteVisit(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            mission_id=UUID("00000000-0000-0000-0000-000000000002"),
            status=SiteVisitStatus.COPRESENCE_OK,
            checked_in_at=datetime(2026, 7, 14, 14, 0, tzinfo=UTC),
            checked_out_at=datetime(2026, 7, 14, 14, 30, tzinfo=UTC),
        )

        with pytest.raises(AlreadyCheckedOut):
            check_out(visit, now=datetime.now(UTC))


class TestCoPresenceRulesModeA:
    """Co-présence mode A (GPS) — délai + distance."""

    def test_copresence_valid(self):
        """Délai ≤ 15min, distance ≤ 100m = OK."""
        inspector_time = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        host_time = datetime(2026, 7, 14, 14, 10, tzinfo=UTC)
        distance_m = 50.0

        params = CoPresenceParams(
            max_delay=timedelta(minutes=15),
            max_distance_meters=100.0,
        )

        # Should not raise
        assert_copresence_mode_a(inspector_time, host_time, distance_m, params)

    def test_copresence_valid_boundary_delay(self):
        """Délai exactement 15 min = OK."""
        inspector_time = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        host_time = datetime(2026, 7, 14, 14, 15, tzinfo=UTC)
        distance_m = 50.0

        params = CoPresenceParams(
            max_delay=timedelta(minutes=15),
            max_distance_meters=100.0,
        )

        assert_copresence_mode_a(inspector_time, host_time, distance_m, params)

    def test_copresence_invalid_delay_exceeded(self):
        """Délai > 15 min = erreur."""
        inspector_time = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        host_time = datetime(2026, 7, 14, 14, 16, tzinfo=UTC)  # 16 min
        distance_m = 50.0

        params = CoPresenceParams(
            max_delay=timedelta(minutes=15),
            max_distance_meters=100.0,
        )

        with pytest.raises(DomainError) as exc_info:
            assert_copresence_mode_a(inspector_time, host_time, distance_m, params)
        assert "délai" in str(exc_info.value).lower()

    def test_copresence_valid_boundary_distance(self):
        """Distance exactement 100m = OK."""
        inspector_time = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        host_time = datetime(2026, 7, 14, 14, 10, tzinfo=UTC)
        distance_m = 100.0

        params = CoPresenceParams(
            max_delay=timedelta(minutes=15),
            max_distance_meters=100.0,
        )

        assert_copresence_mode_a(inspector_time, host_time, distance_m, params)

    def test_copresence_invalid_distance_exceeded(self):
        """Distance > 100m = erreur."""
        inspector_time = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        host_time = datetime(2026, 7, 14, 14, 10, tzinfo=UTC)
        distance_m = 120.0

        params = CoPresenceParams(
            max_delay=timedelta(minutes=15),
            max_distance_meters=100.0,
        )

        with pytest.raises(DomainError) as exc_info:
            assert_copresence_mode_a(inspector_time, host_time, distance_m, params)
        assert "distance" in str(exc_info.value).lower()

    def test_copresence_zero_delay(self):
        """Même moment = OK."""
        inspector_time = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        host_time = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        distance_m = 20.0

        params = CoPresenceParams(
            max_delay=timedelta(minutes=15),
            max_distance_meters=100.0,
        )

        assert_copresence_mode_a(inspector_time, host_time, distance_m, params)

    def test_copresence_zero_distance(self):
        """Même localisation = OK."""
        inspector_time = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        host_time = datetime(2026, 7, 14, 14, 5, tzinfo=UTC)
        distance_m = 0.0

        params = CoPresenceParams(
            max_delay=timedelta(minutes=15),
            max_distance_meters=100.0,
        )

        assert_copresence_mode_a(inspector_time, host_time, distance_m, params)


class TestCoPresenceRulesCustom:
    """Co-présence avec paramètres custom."""

    def test_strict_copresence_5min_50m(self):
        """Stricter: 5 min max délai, 50m max distance."""
        inspector_time = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        host_time = datetime(2026, 7, 14, 14, 3, tzinfo=UTC)
        distance_m = 40.0

        params = CoPresenceParams(
            max_delay=timedelta(minutes=5),
            max_distance_meters=50.0,
        )

        assert_copresence_mode_a(inspector_time, host_time, distance_m, params)

    def test_strict_copresence_boundary_fail_delay(self):
        """6 min > 5 min max = fail."""
        inspector_time = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        host_time = datetime(2026, 7, 14, 14, 6, tzinfo=UTC)
        distance_m = 40.0

        params = CoPresenceParams(
            max_delay=timedelta(minutes=5),
            max_distance_meters=50.0,
        )

        with pytest.raises(DomainError):
            assert_copresence_mode_a(inspector_time, host_time, distance_m, params)

    def test_relaxed_copresence_30min_200m(self):
        """Relaxed: 30 min max, 200m max."""
        inspector_time = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        host_time = datetime(2026, 7, 14, 14, 25, tzinfo=UTC)
        distance_m = 150.0

        params = CoPresenceParams(
            max_delay=timedelta(minutes=30),
            max_distance_meters=200.0,
        )

        assert_copresence_mode_a(inspector_time, host_time, distance_m, params)


class TestNaiveDatetimeNormalization:
    """Datetimes naïfs normalisés en UTC."""

    def test_naive_datetimes_handled(self):
        """Datetimes naïfs → normalisés en UTC."""
        inspector_time = datetime(2026, 7, 14, 14, 0)  # naive
        host_time = datetime(2026, 7, 14, 14, 10)  # naive
        distance_m = 50.0

        params = CoPresenceParams(
            max_delay=timedelta(minutes=15),
            max_distance_meters=100.0,
        )

        # Should not raise (naive → aware conversion)
        assert_copresence_mode_a(inspector_time, host_time, distance_m, params)
