"""Rôles applicatifs du système SIGIS."""

from enum import StrEnum


class Role(StrEnum):
    """
    Rôles hiérarchiques du système.

    SUPER_ADMIN       — administrateur technique de la plateforme.
    NATIONAL_ADMIN    — responsable national (MINESEC / MINSUB).
    REGIONAL_SUPERVISOR — superviseur académique / délégation régionale.
    INSPECTOR         — inspecteur de terrain.
    HOST              — responsable d'accueil de l'établissement.
    """

    SUPER_ADMIN = "SUPER_ADMIN"
    NATIONAL_ADMIN = "NATIONAL_ADMIN"
    REGIONAL_SUPERVISOR = "REGIONAL_SUPERVISOR"
    INSPECTOR = "INSPECTOR"
    HOST = "HOST"
