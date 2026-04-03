"""Cycle de vie SiteVisit — états à formaliser (machine à états V1)."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from domain.shared.value_objects.host_validation_mode import HostValidationMode


class SiteVisitStatus(StrEnum):
    SCHEDULED = "scheduled"
    CHECKED_IN = "checked_in"
    PENDING_HOST = "pending_host_validation"
    COPRESENCE_OK = "copresence_validated"
    CHECKED_OUT = "checked_out"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class SiteVisit:
    id: UUID
    mission_id: UUID
    status: SiteVisitStatus = SiteVisitStatus.SCHEDULED
    host_validation_mode: HostValidationMode | None = None
    checked_in_at: datetime | None = None
    checked_out_at: datetime | None = None
    # transitions métier : méthodes dédiées une fois les invariants figés
