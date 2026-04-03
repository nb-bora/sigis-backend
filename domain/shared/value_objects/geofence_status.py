from enum import StrEnum


class GeofenceStatus(StrEnum):
    """Codes techniques ; libellés FR glossaire (confirmée, probable, hors zone)."""

    OK = "OK"
    APPROXIMATE = "APPROXIMATE"
    REJECTED = "REJECTED"
