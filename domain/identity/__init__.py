"""Module d'identité : Utilisateurs, rôles, permissions et numéros camerounais."""

from domain.identity.permission import Permission
from domain.identity.role import Role
from domain.identity.role_defaults import ROLE_DEFAULT_PERMISSIONS, default_permissions_for
from domain.identity.user import User
from domain.identity.value_objects.phone_number import CameroonPhoneNumber, InvalidPhoneNumber

__all__ = [
    "Role",
    "Permission",
    "ROLE_DEFAULT_PERMISSIONS",
    "default_permissions_for",
    "User",
    "CameroonPhoneNumber",
    "InvalidPhoneNumber",
]
