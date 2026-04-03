"""Exemple de cas d'usage : check-in inspecteur (squelette — à brancher sur repos réels)."""

from dataclasses import dataclass
from uuid import UUID

from domain.errors import DomainError


@dataclass(frozen=True)
class CheckInInspectorCommand:
    mission_id: UUID
    inspector_user_id: UUID
    latitude: float
    longitude: float
    client_request_id: str  # idempotence offline


class CheckInInspector:
    """Orchestration — règles géo détaillées une fois PostGIS branché."""

    def __init__(self, uow_factory: object) -> None:
        self._uow_factory = uow_factory

    async def execute(self, cmd: CheckInInspectorCommand) -> None:
        raise DomainError("Non implémenté — brancher UnitOfWork + géofence PostGIS.", code="NOT_IMPLEMENTED")
