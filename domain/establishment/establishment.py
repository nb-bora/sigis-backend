"""Racine d'agrégat Establishment (squelette — IDs et champs à figer avec le glossaire)."""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class Establishment:
    id: UUID
    name: str
    # geometry_version_id: lié à EstablishmentGeometryVersion (PostGIS côté infra)
