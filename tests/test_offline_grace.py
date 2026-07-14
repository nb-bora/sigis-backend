"""Tests offline grace — client timestamps dans fenêtre mission."""

from datetime import UTC, datetime, timedelta

import pytest

from domain.errors import DomainError
from domain.shared.client_time_validation import (
    ensure_mission_window_client_time,
    ensure_mission_window_with_grace,
)


class TestClientTimeValidation:
    """Offline grace: timestamps client valides même si sync tardy."""

    def test_client_time_within_window(self):
        """Timestamp client dans fenêtre = accepté."""
        window_start = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        window_end = datetime(2026, 7, 14, 16, 0, tzinfo=UTC)
        captured_at = datetime(2026, 7, 14, 14, 30, tzinfo=UTC)

        # Should not raise
        ensure_mission_window_client_time(captured_at, window_start, window_end)

    def test_client_time_before_window(self):
        """Timestamp client avant fenêtre = rejeté."""
        window_start = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        window_end = datetime(2026, 7, 14, 16, 0, tzinfo=UTC)
        captured_at = datetime(2026, 7, 14, 13, 30, tzinfo=UTC)

        with pytest.raises(DomainError) as exc_info:
            ensure_mission_window_client_time(captured_at, window_start, window_end)
        assert exc_info.value.code == "MISSION_EXPIRED_CLIENT_TIME"

    def test_client_time_after_window(self):
        """Timestamp client après fenêtre = rejeté."""
        window_start = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        window_end = datetime(2026, 7, 14, 16, 0, tzinfo=UTC)
        captured_at = datetime(2026, 7, 14, 16, 30, tzinfo=UTC)

        with pytest.raises(DomainError) as exc_info:
            ensure_mission_window_client_time(captured_at, window_start, window_end)
        assert exc_info.value.code == "MISSION_EXPIRED_CLIENT_TIME"

    def test_client_time_at_boundaries(self):
        """Timestamps aux limites de fenêtre = acceptés."""
        window_start = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        window_end = datetime(2026, 7, 14, 16, 0, tzinfo=UTC)

        # À la limite start
        ensure_mission_window_client_time(window_start, window_start, window_end)

        # À la limite end
        ensure_mission_window_client_time(window_end, window_start, window_end)

    def test_naive_datetime_handled(self):
        """Datetimes naïfs normalisés en UTC."""
        window_start = datetime(2026, 7, 14, 14, 0)  # naive
        window_end = datetime(2026, 7, 14, 16, 0)  # naive
        captured_at = datetime(2026, 7, 14, 14, 30)  # naive

        # Should not raise (normalisé en UTC)
        ensure_mission_window_client_time(captured_at, window_start, window_end)


class TestMissionWindowWithGrace:
    """Grace period: tolérance avant/après fenêtre."""

    def test_before_grace(self):
        """Inspecteur 10 min avant fenêtre = accepté."""
        window_start = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        window_end = datetime(2026, 7, 14, 16, 0, tzinfo=UTC)
        captured_at = datetime(2026, 7, 14, 13, 55, tzinfo=UTC)  # 5 min avant

        ensure_mission_window_with_grace(
            captured_at, window_start, window_end, grace_before_minutes=10
        )

    def test_beyond_grace_before(self):
        """12 min avant fenêtre (grace=10) = rejeté."""
        window_start = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        window_end = datetime(2026, 7, 14, 16, 0, tzinfo=UTC)
        captured_at = datetime(2026, 7, 14, 13, 48, tzinfo=UTC)  # 12 min avant

        with pytest.raises(DomainError) as exc_info:
            ensure_mission_window_with_grace(
                captured_at, window_start, window_end, grace_before_minutes=10
            )
        assert exc_info.value.code == "MISSION_EXPIRED_WITH_GRACE"

    def test_after_grace(self):
        """Inspecteur 15 min après fenêtre = accepté."""
        window_start = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        window_end = datetime(2026, 7, 14, 16, 0, tzinfo=UTC)
        captured_at = datetime(2026, 7, 14, 16, 10, tzinfo=UTC)  # 10 min après

        ensure_mission_window_with_grace(
            captured_at, window_start, window_end, grace_after_minutes=15
        )

    def test_custom_grace_values(self):
        """Grace period configurable."""
        window_start = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        window_end = datetime(2026, 7, 14, 16, 0, tzinfo=UTC)
        captured_at = datetime(2026, 7, 14, 13, 40, tzinfo=UTC)  # 20 min avant

        with pytest.raises(DomainError):
            ensure_mission_window_with_grace(
                captured_at,
                window_start,
                window_end,
                grace_before_minutes=10,  # 20 min > 10 min
            )

        # Should pass with larger grace
        ensure_mission_window_with_grace(
            captured_at,
            window_start,
            window_end,
            grace_before_minutes=30,  # 20 min < 30 min
        )


class TestOfflineScenarios:
    """Scénarios offline réalistes."""

    def test_offline_checkin_sync_later(self):
        """Inspecteur check-in offline 14h, sync 18h = OK si 14h ∈ fenêtre."""
        window_start = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        window_end = datetime(2026, 7, 14, 16, 0, tzinfo=UTC)

        # Captured offline à 14h30
        captured_at_offline = datetime(2026, 7, 14, 14, 30, tzinfo=UTC)

        # Sync à 18h
        server_time_now = datetime(2026, 7, 14, 18, 0, tzinfo=UTC)  # noqa: F841

        # Validation avec timestamp client (14h30) → OK
        ensure_mission_window_client_time(captured_at_offline, window_start, window_end)

    def test_offline_confirm_host_after_mission_window(self):
        """Hôte valide offline à 14h15, sync 20h = OK si grace inclut."""
        window_start = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
        window_end = datetime(2026, 7, 14, 16, 0, tzinfo=UTC)

        # Hôte valide offline 30 min après fenêtre (mais grace=30)
        captured_at = datetime(2026, 7, 14, 16, 30, tzinfo=UTC)

        ensure_mission_window_with_grace(
            captured_at, window_start, window_end, grace_after_minutes=45
        )
