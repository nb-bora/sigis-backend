from uuid import UUID

from fastapi import APIRouter

from api.deps import UoW, UserId
from api.v1.schemas import CheckInBody, CheckOutBody, ConfirmHostBody
from application.use_cases.check_in_inspector import CheckInInspector, CheckInInspectorCommand
from application.use_cases.check_out_visit import CheckOutVisit, CheckOutCommand
from application.use_cases.confirm_host_presence import ConfirmHostPresence, ConfirmHostCommand

router = APIRouter(tags=["site-visits"])


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
