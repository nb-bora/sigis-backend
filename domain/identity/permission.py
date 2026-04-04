"""
Permissions applicatives SIGIS.

Chaque permission correspond à un ensemble d'endpoints de l'API.
Les permissions sont attribuées aux rôles et peuvent être modifiées
par un administrateur (ajout / retrait sans doublons).
"""

from __future__ import annotations

from enum import StrEnum


class Permission(StrEnum):
    """
    Catalogue exhaustif des droits d'accès de la plateforme SIGIS.

    Nomenclature : <DOMAINE>_<ACTION>
    """

    # ── Établissements ────────────────────────────────────────────────────
    ESTABLISHMENT_CREATE = "ESTABLISHMENT_CREATE"
    ESTABLISHMENT_READ = "ESTABLISHMENT_READ"
    ESTABLISHMENT_UPDATE = "ESTABLISHMENT_UPDATE"

    # ── Missions ──────────────────────────────────────────────────────────
    MISSION_CREATE = "MISSION_CREATE"
    MISSION_READ = "MISSION_READ"
    MISSION_UPDATE = "MISSION_UPDATE"
    MISSION_APPROVE = "MISSION_APPROVE"
    MISSION_CANCEL = "MISSION_CANCEL"
    MISSION_REASSIGN = "MISSION_REASSIGN"
    MISSION_OUTCOME_WRITE = "MISSION_OUTCOME_WRITE"

    # ── Visites de site ───────────────────────────────────────────────────
    VISIT_CHECKIN = "VISIT_CHECKIN"
    VISIT_HOST_CONFIRM = "VISIT_HOST_CONFIRM"
    VISIT_CHECKOUT = "VISIT_CHECKOUT"
    VISIT_READ = "VISIT_READ"

    # ── Signalements (Exception Requests) ─────────────────────────────────
    EXCEPTION_CREATE = "EXCEPTION_CREATE"
    EXCEPTION_READ = "EXCEPTION_READ"
    EXCEPTION_UPDATE_STATUS = "EXCEPTION_UPDATE_STATUS"
    EXCEPTION_MANAGE = "EXCEPTION_MANAGE"

    # ── Utilisateurs ──────────────────────────────────────────────────────
    USER_LIST = "USER_LIST"
    USER_READ = "USER_READ"
    USER_UPDATE = "USER_UPDATE"
    USER_MANAGE_ROLES = "USER_MANAGE_ROLES"

    # ── Auth (création de comptes, réservé aux admins) ────────────────────
    AUTH_REGISTER_USER = "AUTH_REGISTER_USER"

    # ── Rôles & permissions (administration des ACL) ──────────────────────
    ROLE_READ = "ROLE_READ"
    ROLE_MANAGE_PERMISSIONS = "ROLE_MANAGE_PERMISSIONS"

    REPORT_READ = "REPORT_READ"
    AUDIT_READ = "AUDIT_READ"
