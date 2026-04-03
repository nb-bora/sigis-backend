from uuid import UUID

from fastapi import APIRouter

from api.deps import UoW, UserId
from api.v1.schemas import CheckInBody, CheckOutBody, ConfirmHostBody
from application.use_cases.check_in_inspector import CheckInInspector, CheckInInspectorCommand
from application.use_cases.check_out_visit import CheckOutCommand, CheckOutVisit
from application.use_cases.confirm_host_presence import ConfirmHostCommand, ConfirmHostPresence
from domain.errors import NotFound

router = APIRouter(tags=["site-visits"])


@router.get("/site-visits/{site_visit_id}")
async def get_site_visit(site_visit_id: UUID, uow: UoW, _user: UserId) -> dict[str, object]:
    assert uow.site_visits is not None
    visit = await uow.site_visits.get_by_id(site_visit_id)
    if visit is None:
        raise NotFound("Visite introuvable.")
    return {
        "id": str(visit.id),
        "mission_id": str(visit.mission_id),
        "status": visit.status.value,
        "host_validation_mode": (
            visit.host_validation_mode.value if visit.host_validation_mode else None
        ),
        "checked_in_at": visit.checked_in_at.isoformat() if visit.checked_in_at else None,
        "checked_out_at": visit.checked_out_at.isoformat() if visit.checked_out_at else None,
        "inspector_lat": visit.inspector_lat,
        "inspector_lon": visit.inspector_lon,
        "host_lat": visit.host_lat,
        "host_lon": visit.host_lon,
    }


@router.post("/missions/{mission_id}/check-in")
async def check_in(
    mission_id: UUID,
    body: CheckInBody,
    uow: UoW,
    user: UserId,
) -> dict[str, object]:
    uc = CheckInInspector(uow)
    return await uc.execute(
        CheckInInspectorCommand(
            mission_id=mission_id,
            inspector_user_id=user,
            latitude=body.latitude,
            longitude=body.longitude,
            client_request_id=body.client_request_id,
            host_validation_mode=body.host_validation_mode,
        )
    )


@router.post("/site-visits/{site_visit_id}/host-confirmation")
async def confirm_host(
    site_visit_id: UUID,
    body: ConfirmHostBody,
    uow: UoW,
    user: UserId,
) -> dict[str, object]:
    uc = ConfirmHostPresence(uow)
    return await uc.execute(
        ConfirmHostCommand(
            site_visit_id=site_visit_id,
            mission_id=body.mission_id,
            host_user_id=user,
            client_request_id=body.client_request_id,
            latitude=body.latitude,
            longitude=body.longitude,
            qr_token=body.qr_token,
            sms_code=body.sms_code,
        )
    )


@router.post("/site-visits/{site_visit_id}/check-out")
async def check_out_ep(
    site_visit_id: UUID,
    body: CheckOutBody,
    uow: UoW,
    user: UserId,
) -> dict[str, object]:
    uc = CheckOutVisit(uow)
    return await uc.execute(
        CheckOutCommand(
            site_visit_id=site_visit_id,
            mission_id=body.mission_id,
            inspector_user_id=user,
            client_request_id=body.client_request_id,
        )
    )
