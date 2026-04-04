"""Rapport de mission (V2 minimal — synthèse structurée)."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class MissionOutcome:
    id: UUID
    mission_id: UUID
    summary: str
    notes: str | None
    compliance_level: str | None
    created_at: datetime
    created_by_user_id: UUID
