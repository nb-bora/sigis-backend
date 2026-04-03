"""Mission : inspecteur, établissement, fenêtre horaire."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class MissionStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Mission:
    id: UUID
    establishment_id: UUID
    inspector_id: UUID
    window_start: datetime
    window_end: datetime
    status: MissionStatus = MissionStatus.PLANNED
    """Jeton affiché sur QR / corrélation mission ↔ établissement (mode B)."""
    host_token: UUID | None = None
    """Code SMS attendu (V1 dev — à durcir en prod)."""
    sms_code: str | None = None
