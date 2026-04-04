"""Exports CSV et indicateurs légers (pilotage)."""

from __future__ import annotations

import csv
import io
from collections import Counter

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from api.deps import RequirePermissionDep, UoW, UserId
from domain.identity.permission import Permission

router = APIRouter(prefix="/reports", tags=["Pilotage"])


@router.get(
    "/summary",
    dependencies=[Depends(RequirePermissionDep(Permission.REPORT_READ))],
    summary="Indicateurs agrégés (missions, signalements)",
)
async def reports_summary(uow: UoW, _user: UserId) -> dict[str, object]:
    assert uow.missions is not None
    assert uow.exception_requests is not None
    assert uow.establishments is not None
    assert uow.users is not None
    missions = await uow.missions.list_all()
    exceptions = await uow.exception_requests.list_all()
    m_by = Counter(m.status.value for m in missions)
    e_by = Counter(e.status.value for e in exceptions)
    _, establishments_total = await uow.establishments.list_page(0, 1)
    _, users_total = await uow.users.list_page(0, 1)
    return {
        "missions_total": len(missions),
        "missions_by_status": dict(m_by),
        "exception_requests_total": len(exceptions),
        "exception_requests_by_status": dict(e_by),
        "establishments_total": establishments_total,
        "users_total": users_total,
    }


@router.get(
    "/missions.csv",
    dependencies=[Depends(RequirePermissionDep(Permission.REPORT_READ))],
    summary="Export CSV des missions",
)
async def export_missions_csv(
    uow: UoW,
    _user: UserId,
) -> StreamingResponse:
    assert uow.missions is not None
    rows = await uow.missions.list_all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "id",
            "establishment_id",
            "inspector_id",
            "status",
            "window_start",
            "window_end",
            "territory_code",
        ]
    )
    for m in rows:
        est = await uow.establishments.get_by_id(m.establishment_id)
        terr = est.territory_code if est else ""
        w.writerow(
            [
                str(m.id),
                str(m.establishment_id),
                str(m.inspector_id),
                m.status.value,
                m.window_start.isoformat(),
                m.window_end.isoformat(),
                terr or "",
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="missions.csv"'},
    )
