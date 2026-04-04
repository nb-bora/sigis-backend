"""Entité domaine : Utilisateur SIGIS."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from domain.identity.role import Role


@dataclass
class User:
    """
    Agrégat racine représentant un utilisateur du système SIGIS.

    ``hashed_password`` n'est jamais exposé directement via l'API ;
    il est transmis uniquement entre la couche application et
    l'infrastructure de persistance.
    """

    id: UUID
    email: str
    full_name: str
    phone_number: str  # stocké en E.164 : +237XXXXXXXXX
    hashed_password: str
    role: Role
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = field(default=None)
