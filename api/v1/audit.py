"""Journal d'audit applicatif (lecture)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import RequirePermissionDep, UoW, UserId
from common.pagination import Page, PageParams
from domain.audit.audit_log_entry import AuditLogEntry
from domain.identity.permission import Permission

router = APIRouter(prefix="/audit-logs", tags=["Audit"])


def _entry_dict(e: AuditLogEntry) -> dict[str, object]:
    return {
        "id": str(e.id),
        "created_at": e.created_at.isoformat(),
        "actor_user_id": str(e.actor_user_id) if e.actor_user_id else None,
        "action": e.action,
        "resource_type": e.resource_type,
        "resource_id": e.resource_id,
        "payload_json": e.payload_json,
        "request_id": e.request_id,
    }


@router.get(
    "",
    dependencies=[Depends(RequirePermissionDep(Permission.AUDIT_READ))],
    summary="Lister les entrées d'audit",
)
async def list_audit_logs(
    uow: UoW,
    _user: UserId,
    pagination: PageParams = Depends(),
) -> Page[dict[str, object]]:
    assert uow.audit_logs is not None
    items, total = await uow.audit_logs.list_page(pagination.skip, pagination.limit)
    return Page(
        items=[_entry_dict(e) for e in items],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )
