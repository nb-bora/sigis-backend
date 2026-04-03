"""Routes supervision — signalements (mini-workflow V1)."""

from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel

from api.deps import UoW, UserId
from domain.errors import NotFound
from domain.exception_request.exception_request import ExceptionRequest, ExceptionRequestStatus

router = APIRouter(prefix="/exception-requests", tags=["exception-requests"])


class UpdateStatusBody(BaseModel):
    status: ExceptionRequestStatus


def _exc_dict(e: ExceptionRequest) -> dict[str, object]:
    return {
        "id": str(e.id),
        "mission_id": str(e.mission_id),
        "author_user_id": str(e.author_user_id),
        "created_at": e.created_at.isoformat(),
        "status": e.status.value,
        "message": e.message,
    }


@router.get("")
async def list_exception_requests(
    uow: UoW,
    _user: UserId,
    status: str | None = Query(default=None, description="Filtre par statut"),
) -> list[dict[str, object]]:
    """File de supervision : tous les signalements, filtrables par statut."""
    assert uow.exception_requests is not None
    items = await uow.exception_requests.list_all(status=status)
    return [_exc_dict(e) for e in items]


@router.get("/{exception_id}")
async def get_exception_request(exception_id: UUID, uow: UoW, _user: UserId) -> dict[str, object]:
    assert uow.exception_requests is not None
    exc = await uow.exception_requests.get_by_id(exception_id)
    if exc is None:
        raise NotFound("Signalement introuvable.")
    return _exc_dict(exc)


@router.patch("/{exception_id}/status")
async def update_exception_status(
    exception_id: UUID,
    body: UpdateStatusBody,
    uow: UoW,
    _user: UserId,
) -> dict[str, object]:
    """Supervision : faire passer un signalement à acknowledged / resolved / escalated."""
    assert uow.exception_requests is not None
    exc = await uow.exception_requests.get_by_id(exception_id)
    if exc is None:
        raise NotFound("Signalement introuvable.")
    await uow.exception_requests.update_status(exception_id, body.status)
    return {"id": str(exception_id), "status": body.status.value}
