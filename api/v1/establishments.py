from uuid import UUID

from fastapi import APIRouter

from api.deps import UoW, UserId
from api.v1.schemas import CreateEstablishmentBody
from application.use_cases.create_mission import CreateEstablishment, CreateEstablishmentCommand
from domain.errors import NotFound

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


@router.get("")
async def list_establishments(uow: UoW, _user: UserId) -> list[dict[str, object]]:
    assert uow.establishments is not None
    items = await uow.establishments.list_all()
    return [
        {
            "id": str(e.id),
            "name": e.name,
            "center_lat": e.center_lat,
            "center_lon": e.center_lon,
            "radius_strict_m": e.radius_strict_m,
            "radius_relaxed_m": e.radius_relaxed_m,
            "geometry_version": e.geometry_version,
        }
        for e in items
    ]


@router.get("/{establishment_id}")
async def get_establishment(establishment_id: UUID, uow: UoW, _user: UserId) -> dict[str, object]:
    assert uow.establishments is not None
    est = await uow.establishments.get_by_id(establishment_id)
    if est is None:
        raise NotFound("Établissement introuvable.")
    return {
        "id": str(est.id),
        "name": est.name,
        "center_lat": est.center_lat,
        "center_lon": est.center_lon,
        "radius_strict_m": est.radius_strict_m,
        "radius_relaxed_m": est.radius_relaxed_m,
        "geometry_version": est.geometry_version,
    }
