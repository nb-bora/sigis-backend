"""Workflows mission : validation hiérarchique, annulation structurée, rapport (MissionOutcome)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from application.ports.unit_of_work import UnitOfWork
from domain.errors import Conflict, NotFound
from domain.mission.mission import Mission, MissionStatus
from domain.mission.mission_outcome import MissionOutcome


@dataclass(frozen=True)
class ApproveMissionCommand:
    mission_id: UUID
    approver_user_id: UUID


class ApproveMission:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, cmd: ApproveMissionCommand) -> Mission:
        mission = await self._uow.missions.get_by_id(cmd.mission_id)
        if mission is None:
            raise NotFound("Mission introuvable.")
        if mission.status != MissionStatus.DRAFT:
            raise Conflict("Seules les missions en brouillon (draft) peuvent être validées.")
        mission.status = MissionStatus.PLANNED
        await self._uow.missions.update(mission)
        return mission


@dataclass(frozen=True)
class CancelMissionCommand:
    mission_id: UUID
    reason: str
    cancelled_by_user_id: UUID


class CancelMission:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, cmd: CancelMissionCommand) -> Mission:
        mission = await self._uow.missions.get_by_id(cmd.mission_id)
        if mission is None:
            raise NotFound("Mission introuvable.")
        if mission.status == MissionStatus.COMPLETED:
            raise Conflict("Une mission terminée ne peut pas être annulée.")
        mission.status = MissionStatus.CANCELLED
        mission.cancellation_reason = cmd.reason[:4000]
        mission.cancelled_at = datetime.now(UTC)
        mission.cancelled_by_user_id = cmd.cancelled_by_user_id
        await self._uow.missions.update(mission)
        return mission


@dataclass(frozen=True)
class SubmitMissionOutcomeCommand:
    mission_id: UUID
    summary: str
    notes: str | None
    compliance_level: str | None
    author_user_id: UUID


class SubmitMissionOutcome:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, cmd: SubmitMissionOutcomeCommand) -> MissionOutcome:
        mission = await self._uow.missions.get_by_id(cmd.mission_id)
        if mission is None:
            raise NotFound("Mission introuvable.")
        existing = await self._uow.mission_outcomes.get_by_mission_id(cmd.mission_id)
        if existing is not None:
            raise Conflict("Un rapport existe déjà pour cette mission.")
        outcome = MissionOutcome(
            id=uuid4(),
            mission_id=cmd.mission_id,
            summary=cmd.summary[:8000],
            notes=cmd.notes[:8000] if cmd.notes else None,
            compliance_level=cmd.compliance_level,
            created_at=datetime.now(UTC),
            created_by_user_id=cmd.author_user_id,
        )
        await self._uow.mission_outcomes.save(outcome)
        return outcome


@dataclass(frozen=True)
class ReassignInspectorCommand:
    mission_id: UUID
    new_inspector_id: UUID
    actor_user_id: UUID


class ReassignInspector:
    """Réaffecte l'inspecteur et conserve la trace via previous_mission_id (chaîne simple)."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, cmd: ReassignInspectorCommand) -> Mission:
        old = await self._uow.missions.get_by_id(cmd.mission_id)
        if old is None:
            raise NotFound("Mission introuvable.")
        if old.status in (MissionStatus.COMPLETED, MissionStatus.CANCELLED):
            raise Conflict("Mission terminée ou annulée : réaffectation impossible.")
        await self._uow.users.get_by_id(cmd.new_inspector_id)
        new_id = uuid4()
        clone = Mission(
            id=new_id,
            establishment_id=old.establishment_id,
            inspector_id=cmd.new_inspector_id,
            window_start=old.window_start,
            window_end=old.window_end,
            status=MissionStatus.PLANNED,
            host_token=uuid4(),
            sms_code=old.sms_code,
            designated_host_user_id=old.designated_host_user_id,
            objective=old.objective,
            plan_reference=old.plan_reference,
            requires_approval=False,
            previous_mission_id=old.id,
        )
        old.status = MissionStatus.CANCELLED
        old.cancellation_reason = "Réaffectation vers une nouvelle mission."
        old.cancelled_at = datetime.now(UTC)
        old.cancelled_by_user_id = cmd.actor_user_id
        await self._uow.missions.update(old)
        await self._uow.missions.save(clone)
        return clone
