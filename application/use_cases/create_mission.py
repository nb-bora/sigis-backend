"""Création mission (admin / outil) — génère host_token pour QR."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from application.ports.unit_of_work import UnitOfWork
from domain.errors import NotFound
from domain.establishment.establishment import Establishment
from domain.mission.mission import Mission, MissionStatus


@dataclass(frozen=True)
class CreateMissionCommand:
    establishment_id: UUID
    inspector_id: UUID
    window_start: datetime
    window_end: datetime
    sms_code: str | None = None
    objective: str | None = None
    plan_reference: str | None = None
    requires_approval: bool = False
    designated_host_user_id: UUID | None = None


class CreateMission:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, cmd: CreateMissionCommand) -> dict[str, object]:
        est = await self._uow.establishments.get_by_id(cmd.establishment_id)
        if est is None:
            raise NotFound("Établissement introuvable.")

        # Vérifie que l'inspecteur existe (lève NotFound sinon)
        await self._uow.users.get_by_id(cmd.inspector_id)

        mid = uuid4()
        status = MissionStatus.DRAFT if cmd.requires_approval else MissionStatus.PLANNED
        mission = Mission(
            id=mid,
            establishment_id=cmd.establishment_id,
            inspector_id=cmd.inspector_id,
            window_start=cmd.window_start,
            window_end=cmd.window_end,
            status=status,
            host_token=uuid4(),
            sms_code=cmd.sms_code,
            objective=cmd.objective,
            plan_reference=cmd.plan_reference,
            requires_approval=cmd.requires_approval,
            designated_host_user_id=cmd.designated_host_user_id,
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
    minesec_code: str | None = None
    establishment_type: str = "other"
    contact_email: str | None = None
    contact_phone: str | None = None
    territory_code: str | None = None
    parent_establishment_id: UUID | None = None
    designated_host_user_id: UUID | None = None


class CreateEstablishment:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, cmd: CreateEstablishmentCommand) -> dict[str, object]:

        eid = uuid4()
        est = Establishment(
            id=eid,
            name=cmd.name,
            center_lat=cmd.center_lat,
            center_lon=cmd.center_lon,
            radius_strict_m=cmd.radius_strict_m,
            radius_relaxed_m=cmd.radius_relaxed_m,
            geometry_version=1,
            minesec_code=cmd.minesec_code,
            establishment_type=cmd.establishment_type,
            contact_email=cmd.contact_email,
            contact_phone=cmd.contact_phone,
            territory_code=cmd.territory_code,
            parent_establishment_id=cmd.parent_establishment_id,
            designated_host_user_id=cmd.designated_host_user_id,
        )
        await self._uow.establishments.add(est)
        return {"establishment_id": str(eid)}
