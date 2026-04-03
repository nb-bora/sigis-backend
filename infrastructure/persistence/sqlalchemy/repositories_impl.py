from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.establishment.establishment import Establishment
from domain.mission.mission import Mission
from domain.site_visit.site_visit import SiteVisit
from infrastructure.persistence.mappers import (
    apply_site_visit_to_row,
    establishment_to_domain,
    mission_to_domain,
    site_visit_to_domain,
)
from infrastructure.persistence.sqlalchemy.models import (
    EstablishmentModel,
    MissionModel,
    SiteVisitModel,
)


class EstablishmentRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, establishment_id: UUID) -> Establishment | None:
        row = await self._session.get(EstablishmentModel, establishment_id)
        return establishment_to_domain(row) if row else None

    async def list_all(self) -> list[Establishment]:
        result = await self._session.execute(select(EstablishmentModel))
        return [establishment_to_domain(r) for r in result.scalars().all()]

    async def add(self, est: Establishment) -> None:
        self._session.add(
            EstablishmentModel(
                id=est.id,
                name=est.name,
                center_lat=est.center_lat,
                center_lon=est.center_lon,
                radius_strict_m=est.radius_strict_m,
                radius_relaxed_m=est.radius_relaxed_m,
                geometry_version=est.geometry_version,
            )
        )


class MissionRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, mission_id: UUID) -> Mission | None:
        row = await self._session.get(MissionModel, mission_id)
        return mission_to_domain(row) if row else None

    async def list_all(
        self,
        inspector_id: UUID | None = None,
        establishment_id: UUID | None = None,
        status: str | None = None,
    ) -> list[Mission]:
        q = select(MissionModel)
        if inspector_id is not None:
            q = q.where(MissionModel.inspector_id == inspector_id)
        if establishment_id is not None:
            q = q.where(MissionModel.establishment_id == establishment_id)
        if status is not None:
            q = q.where(MissionModel.status == status)
        result = await self._session.execute(q)
        return [mission_to_domain(r) for r in result.scalars().all()]

    async def save(self, mission: Mission) -> None:
        row = await self._session.get(MissionModel, mission.id)
        if row is None:
            if mission.host_token is None:
                raise ValueError("host_token requis pour persister une mission.")
            self._session.add(
                MissionModel(
                    id=mission.id,
                    establishment_id=mission.establishment_id,
                    inspector_id=mission.inspector_id,
                    window_start=mission.window_start,
                    window_end=mission.window_end,
                    status=mission.status.value,
                    host_token=mission.host_token,
                    sms_code=mission.sms_code,
                )
            )
            return
        row.status = mission.status.value
        row.window_start = mission.window_start
        row.window_end = mission.window_end
        if mission.host_token is not None:
            row.host_token = mission.host_token
        row.sms_code = mission.sms_code


class SiteVisitRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, site_visit_id: UUID) -> SiteVisit | None:
        row = await self._session.get(SiteVisitModel, site_visit_id)
        return site_visit_to_domain(row) if row else None

    async def get_by_mission_id(self, mission_id: UUID) -> SiteVisit | None:
        q = await self._session.execute(
            select(SiteVisitModel).where(SiteVisitModel.mission_id == mission_id)
        )
        row = q.scalar_one_or_none()
        return site_visit_to_domain(row) if row else None

    async def save(self, visit: SiteVisit) -> None:
        row = await self._session.get(SiteVisitModel, visit.id)
        if row is None:
            new = SiteVisitModel(
                id=visit.id,
                mission_id=visit.mission_id,
                status=visit.status.value,
                host_validation_mode=visit.host_validation_mode.value
                if visit.host_validation_mode
                else None,
                checked_in_at=visit.checked_in_at,
                checked_out_at=visit.checked_out_at,
                inspector_lat=visit.inspector_lat,
                inspector_lon=visit.inspector_lon,
                host_lat=visit.host_lat,
                host_lon=visit.host_lon,
            )
            self._session.add(new)
            return
        apply_site_visit_to_row(visit, row)
