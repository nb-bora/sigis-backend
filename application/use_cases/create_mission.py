"""Création mission (admin / outil) — génère host_token pour QR."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from domain.establishment.establishment import Establishment
from domain.errors import NotFound
from domain.mission.mission import Mission, MissionStatus
from infrastructure.persistence.sqlalchemy.uow import SqlAlchemyUnitOfWork
from infrastructure.persistence.sqlalchemy.user_repo import UserRepositoryImpl


@dataclass(frozen=True)
class CreateMissionCommand:
    establishment_id: UUID
    inspector_id: UUID
    window_start: datetime
    window_end: datetime
    sms_code: str | None = None


class CreateMission:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, cmd: CreateMissionCommand) -> dict[str, object]:
        assert self._uow.missions is not None
        assert self._uow.establishments is not None
        assert self._uow.session is not None

        est = await self._uow.establishments.get_by_id(cmd.establishment_id)
        if est is None:
            raise NotFound("Établissement introuvable.")

        users = UserRepositoryImpl(self._uow.session)
        await users.ensure_exists(cmd.inspector_id)

        mid = uuid4()
        mission = Mission(
            id=mid,
            establishment_id=cmd.establishment_id,
            inspector_id=cmd.inspector_id,
            window_start=cmd.window_start,
            window_end=cmd.window_end,
            status=MissionStatus.PLANNED,
            host_token=uuid4(),
            sms_code=cmd.sms_code,
        )
        await self._uow.missions.save(mission)
        return {
            "mission_id": str(mission.id),
            "host_token": str(mission.host_token),
            "status": mission.status.value,
        }


@dataclass(frozen=True)
class CreateEstablishmentCommand:
    name: str
    center_lat: float
    center_lon: float
    radius_strict_m: float
    radius_relaxed_m: float


class CreateEstablishment:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, cmd: CreateEstablishmentCommand) -> dict[str, object]:
        assert self._uow.establishments is not None

        eid = uuid4()
        est = Establishment(
            id=eid,
            name=cmd.name,
            center_lat=cmd.center_lat,
            center_lon=cmd.center_lon,
            radius_strict_m=cmd.radius_strict_m,
            radius_relaxed_m=cmd.radius_relaxed_m,
            geometry_version=1,
        )
        await self._uow.establishments.add(est)
        return {"establishment_id": str(eid)}
