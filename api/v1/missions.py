from uuid import UUID

from fastapi import APIRouter, Query

from api.deps import UoW, UserId
from api.v1.schemas import CreateMissionBody, ExceptionBody
from application.use_cases.create_exception_request import (
    CreateExceptionCommand,
    CreateExceptionRequest,
)
from application.use_cases.create_mission import CreateMission, CreateMissionCommand
from domain.errors import NotFound

router = APIRouter(prefix="/missions", tags=["missions"])


@router.post("")
async def create_mission(body: CreateMissionBody, uow: UoW, _user: UserId) -> dict[str, object]:
    uc = CreateMission(uow)
    return await uc.execute(
        CreateMissionCommand(
            establishment_id=body.establishment_id,
            inspector_id=body.inspector_id,
            window_start=body.window_start,
            window_end=body.window_end,
            sms_code=body.sms_code,
        )
    )


@router.get("")
async def list_missions(
    uow: UoW,
    _user: UserId,
    inspector_id: UUID | None = Query(default=None),
    establishment_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
) -> list[dict[str, object]]:
    assert uow.missions is not None
    items = await uow.missions.list_all(
        inspector_id=inspector_id,
        establishment_id=establishment_id,
        status=status,
    )
    return [_mission_dict(m) for m in items]


@router.get("/{mission_id}")
async def get_mission(mission_id: UUID, uow: UoW, _user: UserId) -> dict[str, object]:
    assert uow.missions is not None
    mission = await uow.missions.get_by_id(mission_id)
    if mission is None:
        raise NotFound("Mission introuvable.")
    return _mission_dict(mission)


@router.get("/{mission_id}/site-visit")
async def get_mission_site_visit(mission_id: UUID, uow: UoW, _user: UserId) -> dict[str, object]:
    assert uow.missions is not None
    assert uow.site_visits is not None
    mission = await uow.missions.get_by_id(mission_id)
    if mission is None:
        raise NotFound("Mission introuvable.")
    visit = await uow.site_visits.get_by_mission_id(mission_id)
    if visit is None:
        raise NotFound("Aucune visite démarrée pour cette mission.")
    return _site_visit_dict(visit)


@router.post("/{mission_id}/exception-requests")
async def create_exception(
    mission_id: UUID,
    body: ExceptionBody,
    uow: UoW,
    user: UserId,
) -> dict[str, object]:
    uc = CreateExceptionRequest(uow)
    return await uc.execute(
        CreateExceptionCommand(
            mission_id=mission_id,
            author_user_id=user,
            message=body.message,
        )
    )


@router.get("/{mission_id}/exception-requests")
async def list_mission_exceptions(
    mission_id: UUID, uow: UoW, _user: UserId
) -> list[dict[str, object]]:
    assert uow.missions is not None
    assert uow.exception_requests is not None
    mission = await uow.missions.get_by_id(mission_id)
    if mission is None:
        raise NotFound("Mission introuvable.")
    items = await uow.exception_requests.list_by_mission_id(mission_id)
    return [_exception_dict(e) for e in items]


# ---------------------------------------------------------------------------
# Helpers sérialisation
# ---------------------------------------------------------------------------
def _mission_dict(m: object) -> dict[str, object]:
    from domain.mission.mission import Mission

    assert isinstance(m, Mission)
    return {
        "id": str(m.id),
        "establishment_id": str(m.establishment_id),
        "inspector_id": str(m.inspector_id),
        "window_start": m.window_start.isoformat(),
        "window_end": m.window_end.isoformat(),
        "status": m.status.value,
        "host_token": str(m.host_token) if m.host_token else None,
    }


def _site_visit_dict(v: object) -> dict[str, object]:
    from domain.site_visit.site_visit import SiteVisit

    assert isinstance(v, SiteVisit)
    return {
        "id": str(v.id),
        "mission_id": str(v.mission_id),
        "status": v.status.value,
        "host_validation_mode": v.host_validation_mode.value if v.host_validation_mode else None,
        "checked_in_at": v.checked_in_at.isoformat() if v.checked_in_at else None,
        "checked_out_at": v.checked_out_at.isoformat() if v.checked_out_at else None,
        "inspector_lat": v.inspector_lat,
        "inspector_lon": v.inspector_lon,
        "host_lat": v.host_lat,
        "host_lon": v.host_lon,
    }


def _exception_dict(e: object) -> dict[str, object]:
    from domain.exception_request.exception_request import ExceptionRequest

    assert isinstance(e, ExceptionRequest)
    return {
        "id": str(e.id),
        "mission_id": str(e.mission_id),
        "author_user_id": str(e.author_user_id),
        "created_at": e.created_at.isoformat(),
        "status": e.status.value,
        "message": e.message,
    }
