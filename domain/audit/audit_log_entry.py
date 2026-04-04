"""Entrée de journal d'audit (actions sensibles, corrélation request_id)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class AuditLogEntry:
    id: UUID
    created_at: datetime
    actor_user_id: UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    payload_json: str | None
    request_id: str | None
