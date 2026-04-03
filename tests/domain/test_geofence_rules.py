from domain.shared.geofence_rules import GeofenceParams, geofence_status
from domain.shared.value_objects.geofence_status import GeofenceStatus


def test_geofence_ok() -> None:
    p = GeofenceParams(radius_meters_strict=50.0, radius_meters_relaxed=120.0)
    assert geofence_status(30.0, p) == GeofenceStatus.OK


def test_geofence_approximate() -> None:
    p = GeofenceParams(radius_meters_strict=50.0, radius_meters_relaxed=120.0)
    assert geofence_status(80.0, p) == GeofenceStatus.APPROXIMATE


def test_geofence_rejected() -> None:
    p = GeofenceParams(radius_meters_strict=50.0, radius_meters_relaxed=120.0)
    assert geofence_status(200.0, p) == GeofenceStatus.REJECTED
