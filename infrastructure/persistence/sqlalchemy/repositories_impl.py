from uuid import UUID

from sqlalchemy import func, select
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

    async def list_page(
        self,
        offset: int,
        limit: int,
        *,
        territory_code: str | None = None,
    ) -> tuple[list[Establishment], int]:
        q = select(EstablishmentModel)
        if territory_code is not None:
            q = q.where(EstablishmentModel.territory_code == territory_code)
        count_stmt = select(func.count()).select_from(q.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()
        q = q.order_by(EstablishmentModel.name).offset(offset).limit(limit)
        result = await self._session.execute(q)
        rows = [establishment_to_domain(r) for r in result.scalars().all()]
        return rows, int(total)

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
                minesec_code=est.minesec_code,
                establishment_type=est.establishment_type,
                contact_email=est.contact_email,
                contact_phone=est.contact_phone,
                territory_code=est.territory_code,
                parent_establishment_id=est.parent_establishment_id,
                designated_host_user_id=est.designated_host_user_id,
                geometry_validated_at=est.geometry_validated_at,
                geometry_validated_by_user_id=est.geometry_validated_by_user_id,
            )
        )

    async def update(self, est: Establishment) -> None:
        row = await self._session.get(EstablishmentModel, est.id)
        if row is None:
            return
        row.name = est.name
        row.center_lat = est.center_lat
        row.center_lon = est.center_lon
        row.radius_strict_m = est.radius_strict_m
        row.radius_relaxed_m = est.radius_relaxed_m
        row.geometry_version = est.geometry_version
        row.minesec_code = est.minesec_code
        row.establishment_type = est.establishment_type
        row.contact_email = est.contact_email
        row.contact_phone = est.contact_phone
        row.territory_code = est.territory_code
        row.parent_establishment_id = est.parent_establishment_id
        row.designated_host_user_id = est.designated_host_user_id
        row.geometry_validated_at = est.geometry_validated_at
        row.geometry_validated_by_user_id = est.geometry_validated_by_user_id


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
        territory_code: str | None = None,
    ) -> list[Mission]:
        rows, _ = await self.list_page(
            0,
            10_000,
            inspector_id=inspector_id,
            establishment_id=establishment_id,
            status=status,
            territory_code=territory_code,
        )
        return rows

    def _mission_select_filtered(
        self,
        *,
        inspector_id: UUID | None,
        establishment_id: UUID | None,
        status: str | None,
        territory_code: str | None,
    ):
        q = select(MissionModel)
        if territory_code is not None:
            q = q.join(EstablishmentModel, MissionModel.establishment_id == EstablishmentModel.id)
            q = q.where(EstablishmentModel.territory_code == territory_code)
        if inspector_id is not None:
            q = q.where(MissionModel.inspector_id == inspector_id)
        if establishment_id is not None:
            q = q.where(MissionModel.establishment_id == establishment_id)
        if status is not None:
            q = q.where(MissionModel.status == status)
        return q

    async def list_page(
        self,
        offset: int,
        limit: int,
        *,
        inspector_id: UUID | None = None,
        establishment_id: UUID | None = None,
        status: str | None = None,
        territory_code: str | None = None,
    ) -> tuple[list[Mission], int]:
        q = self._mission_select_filtered(
            inspector_id=inspector_id,
            establishment_id=establishment_id,
            status=status,
            territory_code=territory_code,
        )
        count_stmt = select(func.count()).select_from(q.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()
        q = self._mission_select_filtered(
            inspector_id=inspector_id,
            establishment_id=establishment_id,
            status=status,
            territory_code=territory_code,
        )
        q = q.order_by(MissionModel.window_start.desc()).offset(offset).limit(limit)
        result = await self._session.execute(q)
        return [mission_to_domain(r) for r in result.scalars().all()], int(total)

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
                    designated_host_user_id=mission.designated_host_user_id,
                    objective=mission.objective,
                    plan_reference=mission.plan_reference,
                    requires_approval=mission.requires_approval,
                    cancellation_reason=mission.cancellation_reason,
                    cancelled_at=mission.cancelled_at,
                    cancelled_by_user_id=mission.cancelled_by_user_id,
                    previous_mission_id=mission.previous_mission_id,
                )
            )
            return
        row.status = mission.status.value
        row.window_start = mission.window_start
        row.window_end = mission.window_end
        if mission.host_token is not None:
            row.host_token = mission.host_token
        row.sms_code = mission.sms_code
        row.designated_host_user_id = mission.designated_host_user_id
        row.objective = mission.objective
        row.plan_reference = mission.plan_reference
        row.requires_approval = mission.requires_approval
        row.cancellation_reason = mission.cancellation_reason
        row.cancelled_at = mission.cancelled_at
        row.cancelled_by_user_id = mission.cancelled_by_user_id
        row.previous_mission_id = mission.previous_mission_id
        row.inspector_id = mission.inspector_id
        row.establishment_id = mission.establishment_id

    async def update(self, mission: Mission) -> None:
        await self.save(mission)


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
