"""Mission : inspecteur, établissement, fenêtre horaire."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class MissionStatus(StrEnum):
    """Brouillon si validation hiérarchique requise avant exécution terrain."""

    DRAFT = "draft"
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
    designated_host_user_id: UUID | None = None
    objective: str | None = None
    plan_reference: str | None = None
    requires_approval: bool = False
    cancellation_reason: str | None = None
    cancelled_at: datetime | None = None
    cancelled_by_user_id: UUID | None = None
    previous_mission_id: UUID | None = None
