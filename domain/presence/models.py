"""Modèles de domaine pour preuves de présence (squelette)."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from domain.shared.value_objects.geofence_status import GeofenceStatus


@dataclass
class PresenceProof:
    """Preuve brute (inspecteur / hôte si mode A)."""

    id: UUID
    site_visit_id: UUID
    actor_user_id: UUID
    recorded_at: datetime
    latitude: float
    longitude: float
    geofence_status: GeofenceStatus


@dataclass
class CoPresenceEvent:
    """Émis lorsque la politique de co-présence est satisfaite pour le mode choisi."""

    id: UUID
    site_visit_id: UUID
    validated_at: datetime
