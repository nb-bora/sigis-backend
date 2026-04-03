from dataclasses import dataclass
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
