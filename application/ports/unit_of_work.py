"""Unit of Work — transaction unique par cas d'usage."""

from typing import Protocol

from application.ports.repositories import MissionRepository, SiteVisitRepository


class UnitOfWork(Protocol):
    missions: MissionRepository
    site_visits: SiteVisitRepository

    async def __aenter__(self) -> "UnitOfWork": ...

    async def __aexit__(self, *args: object) -> None: ...

    async def commit(self) -> None: ...
