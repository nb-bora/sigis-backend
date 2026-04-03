"""Règles géofence V1 : point + rayon + deux seuils (nominal / élargi) — logique pure."""

from dataclasses import dataclass

from domain.shared.value_objects.geofence_status import GeofenceStatus


@dataclass(frozen=True, slots=True)
class GeofenceParams:
    """Paramètres pilote — à injecter depuis la config infrastructure."""

    radius_meters_strict: float
    radius_meters_relaxed: float  # couronne « APPROXIMATE »


def geofence_status(
    distance_to_center_meters: float,
    params: GeofenceParams,
) -> GeofenceStatus:
    """distance_to_center_meters : distance du point inspecteur au centre établissement (déjà calculée)."""
    if distance_to_center_meters <= params.radius_meters_strict:
        return GeofenceStatus.OK
    if distance_to_center_meters <= params.radius_meters_relaxed:
        return GeofenceStatus.APPROXIMATE
    return GeofenceStatus.REJECTED
