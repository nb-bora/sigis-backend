"""Mission : inspecteur, établissement, fenêtre horaire."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Mission:
    id: UUID
    establishment_id: UUID
    inspector_id: UUID
    window_start: datetime
    window_end: datetime
