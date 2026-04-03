"""Interfaces de persistance — implémentées dans infrastructure."""

from typing import Protocol
from uuid import UUID

from domain.mission.mission import Mission
from domain.site_visit.site_visit import SiteVisit


class MissionRepository(Protocol):
    async def get_by_id(self, mission_id: UUID) -> Mission | None: ...

    async def save(self, mission: Mission) -> None: ...


class SiteVisitRepository(Protocol):
    async def get_by_id(self, site_visit_id: UUID) -> SiteVisit | None: ...

    async def save(self, site_visit: SiteVisit) -> None: ...
