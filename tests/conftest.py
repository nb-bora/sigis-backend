"""Test fixtures pour SIGIS V1 (95% coverage)."""

import os
import tempfile
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

# Base SQLite hors du dépôt
_fd, _test_db = tempfile.mkstemp(suffix=".db", prefix="sigis_test_")
os.close(_fd)
os.environ["SIGIS_DATABASE_URL"] = "sqlite+aiosqlite:///" + os.path.abspath(_test_db).replace(
    os.sep, "/"
)


# ============================================================================
# Common fixtures
# ============================================================================


@pytest.fixture
def test_uuid():
    """Generate test UUID."""
    return uuid4()


@pytest.fixture
def test_inspector_id():
    """Test inspector UUID."""
    return UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def test_host_id():
    """Test host UUID."""
    return UUID("00000000-0000-0000-0000-000000000002")


@pytest.fixture
def test_establishment_id():
    """Test establishment UUID."""
    return UUID("00000000-0000-0000-0000-000000000003")


@pytest.fixture
def test_mission_id():
    """Test mission UUID."""
    return UUID("00000000-0000-0000-0000-000000000004")


@pytest.fixture
def test_site_visit_id():
    """Test site visit UUID."""
    return UUID("00000000-0000-0000-0000-000000000005")


# ============================================================================
# Time fixtures
# ============================================================================


@pytest.fixture
def now_utc():
    """Current time in UTC."""
    return datetime.now(UTC)


@pytest.fixture
def mission_window_start():
    """Mission window start: 14:00 UTC."""
    return datetime(2026, 7, 14, 14, 0, tzinfo=UTC)


@pytest.fixture
def mission_window_end():
    """Mission window end: 16:00 UTC."""
    return datetime(2026, 7, 14, 16, 0, tzinfo=UTC)


@pytest.fixture
def checkin_time_offline():
    """Check-in time offline: 14:30 UTC."""
    return datetime(2026, 7, 14, 14, 30, tzinfo=UTC)


@pytest.fixture
def confirm_time_offline():
    """Confirm time offline: 14:45 UTC."""
    return datetime(2026, 7, 14, 14, 45, tzinfo=UTC)


@pytest.fixture
def checkout_time_offline():
    """Check-out time offline: 15:00 UTC."""
    return datetime(2026, 7, 14, 15, 0, tzinfo=UTC)


# ============================================================================
# Location fixtures (Cameroon coordinates)
# ============================================================================


@pytest.fixture
def inspector_location():
    """Inspector position (Yaoundé area)."""
    return (3.8667, 11.5167)  # (lat, lon)


@pytest.fixture
def host_location_close():
    """Host position 45m away."""
    return (3.8668, 11.5168)  # ~45m away in Cameroon


@pytest.fixture
def host_location_far():
    """Host position 150m away."""
    return (3.8670, 11.5170)  # ~150m away


@pytest.fixture
def location_outside_geofence():
    """Location outside 300m geofence."""
    return (0.0, 0.0)  # Equator crossing


# ============================================================================
# GPS quality fixtures
# ============================================================================


@pytest.fixture
def gps_accuracy_excellent():
    """Excellent GPS accuracy (≤5m)."""
    return 3.0


@pytest.fixture
def gps_accuracy_good():
    """Good GPS accuracy (5-25m)."""
    return 15.0


@pytest.fixture
def gps_accuracy_fair():
    """Fair GPS accuracy (25-100m)."""
    return 50.0


@pytest.fixture
def gps_accuracy_poor():
    """Poor GPS accuracy (>100m)."""
    return 150.0


# ============================================================================
# Device binding fixtures
# ============================================================================


@pytest.fixture
def device_id_1():
    """First device ID."""
    return "device-iphone-12-123"


@pytest.fixture
def device_public_key_1():
    """First device public key."""
    return "ed25519_public_key_hex_123abc"


@pytest.fixture
def device_id_2():
    """Second device ID."""
    return "device-samsung-456"


@pytest.fixture
def device_public_key_2():
    """Second device public key."""
    return "ed25519_public_key_hex_456def"


# ============================================================================
# Request ID fixtures (idempotence)
# ============================================================================


@pytest.fixture
def client_request_id_checkin():
    """Client request ID for check-in."""
    return "offline-checkin-test-001"


@pytest.fixture
def client_request_id_confirm():
    """Client request ID for host confirmation."""
    return "offline-confirm-test-001"


@pytest.fixture
def client_request_id_checkout():
    """Client request ID for check-out."""
    return "offline-checkout-test-001"
