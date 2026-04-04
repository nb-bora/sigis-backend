"""
Permissions par défaut associées à chaque rôle SIGIS.

Ces valeurs constituent le référentiel de référence utilisé pour
initialiser la table ``role_permissions`` et servir de fallback quand
la base de données n'est pas encore peuplée.

Règles de conception :
- Principe du moindre privilège : chaque rôle n'obtient que les droits
  nécessaires à ses responsabilités métier.
- Les surcharges (ajouts/retraits) sont stockées en base via l'API
  ``PATCH /v1/roles/{role}/permissions``.
- Aucun doublon : un même rôle ne peut avoir deux fois la même permission.
"""

from __future__ import annotations

from domain.identity.permission import Permission
from domain.identity.role import Role

# Toutes les permissions disponibles
_ALL = set(Permission)

# ── Matrice des permissions par défaut ────────────────────────────────────

ROLE_DEFAULT_PERMISSIONS: dict[Role, set[Permission]] = {
    # ─── SUPER_ADMIN : accès total ────────────────────────────────────────
    Role.SUPER_ADMIN: _ALL,
    # ─── NATIONAL_ADMIN : administration opérationnelle ──────────────────
    Role.NATIONAL_ADMIN: {
        Permission.ESTABLISHMENT_CREATE,
        Permission.ESTABLISHMENT_READ,
        Permission.ESTABLISHMENT_UPDATE,
        Permission.MISSION_CREATE,
        Permission.MISSION_READ,
        Permission.MISSION_UPDATE,
        Permission.MISSION_APPROVE,
        Permission.MISSION_CANCEL,
        Permission.MISSION_REASSIGN,
        Permission.MISSION_OUTCOME_WRITE,
        Permission.VISIT_READ,
        Permission.EXCEPTION_READ,
        Permission.EXCEPTION_UPDATE_STATUS,
        Permission.EXCEPTION_MANAGE,
        Permission.USER_LIST,
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.AUTH_REGISTER_USER,
        Permission.ROLE_READ,
        Permission.REPORT_READ,
        Permission.AUDIT_READ,
    },
    # ─── REGIONAL_SUPERVISOR : supervision régionale ─────────────────────
    Role.REGIONAL_SUPERVISOR: {
        Permission.ESTABLISHMENT_READ,
        Permission.MISSION_READ,
        Permission.MISSION_UPDATE,
        Permission.MISSION_APPROVE,
        Permission.MISSION_CANCEL,
        Permission.MISSION_REASSIGN,
        Permission.MISSION_OUTCOME_WRITE,
        Permission.VISIT_READ,
        Permission.EXCEPTION_READ,
        Permission.EXCEPTION_UPDATE_STATUS,
        Permission.EXCEPTION_MANAGE,
        Permission.USER_READ,
        Permission.ROLE_READ,
        Permission.REPORT_READ,
    },
    # ─── INSPECTOR : terrain ─────────────────────────────────────────────
    Role.INSPECTOR: {
        Permission.ESTABLISHMENT_READ,
        Permission.MISSION_READ,
        Permission.MISSION_OUTCOME_WRITE,
        Permission.VISIT_CHECKIN,
        Permission.VISIT_CHECKOUT,
        Permission.VISIT_READ,
        Permission.EXCEPTION_CREATE,
        Permission.EXCEPTION_READ,
        Permission.USER_READ,
        Permission.USER_UPDATE,
    },
    # ─── HOST : responsable d'accueil ─────────────────────────────────────
    Role.HOST: {
        Permission.ESTABLISHMENT_READ,
        Permission.MISSION_READ,
        Permission.VISIT_HOST_CONFIRM,
        Permission.VISIT_READ,
        Permission.EXCEPTION_READ,
        Permission.USER_READ,
        Permission.USER_UPDATE,
    },
}


def default_permissions_for(role: Role) -> set[Permission]:
    """Retourne l'ensemble des permissions par défaut d'un rôle."""
    return set(ROLE_DEFAULT_PERMISSIONS.get(role, set()))


def all_default_permissions() -> dict[str, list[str]]:
    """Retourne le dictionnaire complet rôle → liste de permissions (pour init DB)."""
    # Toujours dériver de l'énumération Role pour qu'aucun rôle ne soit oublié
    # si ROLE_DEFAULT_PERMISSIONS est incomplet par rapport à Role.
    return {
        role.value: sorted(p.value for p in ROLE_DEFAULT_PERMISSIONS.get(role, set()))
        for role in Role
    }
