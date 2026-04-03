from uuid import UUID

from fastapi import APIRouter

from api.deps import UoW, UserId
from api.v1.schemas import CreateMissionBody, ExceptionBody
from application.use_cases.create_exception_request import CreateExceptionCommand, CreateExceptionRequest
from application.use_cases.create_mission import CreateMission, CreateMissionCommand

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
