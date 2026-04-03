from enum import StrEnum


class GeofenceStatus(StrEnum):
    """Codes techniques — libellés produit FR figés dans le glossaire (confirmée / probable / hors zone)."""

    OK = "OK"
    APPROXIMATE = "APPROXIMATE"
    REJECTED = "REJECTED"
