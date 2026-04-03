from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from domain.shared.value_objects.host_validation_mode import HostValidationMode


class CreateEstablishmentBody(BaseModel):
    name: str
    center_lat: float
    center_lon: float
    radius_strict_m: float = Field(..., description="Seuil strict (m)")
    radius_relaxed_m: float = Field(..., description="Seuil élargi / probable (m)")


class CreateMissionBody(BaseModel):
    establishment_id: UUID
    inspector_id: UUID
    window_start: datetime
    window_end: datetime
    sms_code: str | None = None


class CheckInBody(BaseModel):
    latitude: float
    longitude: float
    client_request_id: str = Field(..., min_length=8, max_length=128)
    host_validation_mode: HostValidationMode


class ConfirmHostBody(BaseModel):
    mission_id: UUID
    client_request_id: str = Field(..., min_length=8, max_length=128)
    latitude: float | None = None
    longitude: float | None = None
    qr_token: UUID | None = None
    sms_code: str | None = None


class CheckOutBody(BaseModel):
    mission_id: UUID
    client_request_id: str = Field(..., min_length=8, max_length=128)


class ExceptionBody(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
