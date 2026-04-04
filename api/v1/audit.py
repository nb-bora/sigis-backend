"""Journal d'audit applicatif (lecture)."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

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


class AuditListFilters:
    """Paramètres de filtre partagés entre la liste paginée et l’export CSV."""

    def __init__(
        self,
        q: str | None = Query(
            None,
            description="Recherche sur l’action, le type de ressource, l’identifiant, request_id ou le JSON de charge utile.",
        ),
        action: str | None = Query(None, description="Filtrer sur une action exacte (ex. mission.approve)."),
        resource_type: str | None = Query(None, description="Filtrer sur un type de ressource (ex. mission)."),
        actor_user_id: UUID | None = Query(None, description="Filtrer sur l’UUID de l’acteur."),
        created_from: datetime | None = Query(None, description="Inclure les entrées à partir de cette date/heure (UTC)."),
        created_to: datetime | None = Query(None, description="Inclure les entrées jusqu’à cette date/heure (UTC)."),
    ) -> None:
        self.q = q
        self.action = action
        self.resource_type = resource_type
        self.actor_user_id = actor_user_id
        self.created_from = created_from
        self.created_to = created_to

    def as_repo_kwargs(self) -> dict[str, object]:
        return {
            "q": self.q,
            "action": self.action,
            "resource_type": self.resource_type,
            "actor_user_id": self.actor_user_id,
            "created_from": self.created_from,
            "created_to": self.created_to,
        }


_MAX_EXPORT_ROWS = 10_000


@router.get(
    "",
    dependencies=[Depends(RequirePermissionDep(Permission.AUDIT_READ))],
    summary="Lister les entrées d’audit",
)
async def list_audit_logs(
    uow: UoW,
    _user: UserId,
    pagination: PageParams = Depends(),
    filters: AuditListFilters = Depends(),
) -> Page[dict[str, object]]:
    assert uow.audit_logs is not None
    items, total = await uow.audit_logs.list_page(
        pagination.skip,
        pagination.limit,
        **filters.as_repo_kwargs(),
    )
    return Page(
        items=[_entry_dict(e) for e in items],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.get(
    "/export.csv",
    dependencies=[Depends(RequirePermissionDep(Permission.AUDIT_READ))],
    summary="Export CSV du journal (même filtres que la liste, plafonné)",
)
async def export_audit_csv(
    uow: UoW,
    _user: UserId,
    filters: AuditListFilters = Depends(),
) -> StreamingResponse:
    assert uow.audit_logs is not None
    rows, total = await uow.audit_logs.list_page(0, _MAX_EXPORT_ROWS, **filters.as_repo_kwargs())
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "created_at",
            "actor_user_id",
            "action",
            "resource_type",
            "resource_id",
            "request_id",
            "payload_json",
        ]
    )
    for e in rows:
        w.writerow(
            [
                e.created_at.isoformat(),
                str(e.actor_user_id) if e.actor_user_id else "",
                e.action,
                e.resource_type,
                e.resource_id or "",
                e.request_id or "",
                e.payload_json or "",
            ]
        )
    buf.seek(0)
    content = "\ufeff" + buf.getvalue()
    filename = "audit_logs.csv"
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-SIGIS-Audit-Total-Matching": str(total),
            "X-SIGIS-Audit-Rows-Exported": str(len(rows)),
        },
    )
