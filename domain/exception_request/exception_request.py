"""Mini-workflow signalement (états à aligner avec le glossaire)."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ExceptionRequestStatus(StrEnum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


@dataclass
class ExceptionRequest:
    id: UUID
    mission_id: UUID
    author_user_id: UUID
    created_at: datetime
    status: ExceptionRequestStatus = ExceptionRequestStatus.NEW
    message: str = ""
    assigned_to_user_id: UUID | None = None
    internal_comment: str | None = None
    sla_due_at: datetime | None = None
    attachment_url: str | None = None
