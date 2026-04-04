"""Écriture du journal d'audit applicatif (non WORM — V1)."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

from application.ports.unit_of_work import UnitOfWork


async def write_audit(
    uow: UnitOfWork,
    *,
    actor_user_id: UUID | None,
    action: str,
    resource_type: str,
    resource_id: UUID | str | None = None,
    payload: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> None:
    rid = str(resource_id) if resource_id is not None else None
    await uow.audit_logs.add(
        id=uuid4(),
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=rid,
        payload_json=json.dumps(payload, default=str) if payload is not None else None,
        request_id=request_id,
    )
