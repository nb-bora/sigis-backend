from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Establishment:
    id: UUID
    name: str
    center_lat: float
    center_lon: float
    radius_strict_m: float
    radius_relaxed_m: float
    geometry_version: int
    minesec_code: str | None = None
    establishment_type: str = "other"
    contact_email: str | None = None
    contact_phone: str | None = None
    territory_code: str | None = None
    parent_establishment_id: UUID | None = None
    designated_host_user_id: UUID | None = None
    geometry_validated_at: datetime | None = None
    geometry_validated_by_user_id: UUID | None = None
