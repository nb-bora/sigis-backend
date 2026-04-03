from fastapi import APIRouter

from api.deps import UoW, UserId
from api.v1.schemas import CreateEstablishmentBody
from application.use_cases.create_mission import CreateEstablishment, CreateEstablishmentCommand

router = APIRouter(prefix="/establishments", tags=["establishments"])


@router.post("")
async def create_establishment(
    body: CreateEstablishmentBody, uow: UoW, _user: UserId
) -> dict[str, object]:
    uc = CreateEstablishment(uow)
    return await uc.execute(
        CreateEstablishmentCommand(
            name=body.name,
            center_lat=body.center_lat,
            center_lon=body.center_lon,
            radius_strict_m=body.radius_strict_m,
            radius_relaxed_m=body.radius_relaxed_m,
        )
    )
