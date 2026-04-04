"""Routes Signalements — mini-workflow supervision V1."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request
from pydantic import BaseModel, Field

from api.deps import RequirePermissionDep, UoW, UserId
from api.v1.schemas import PatchExceptionBody
from common.audit import write_audit
from common.pagination import Page, PageParams
from domain.errors import NotFound
from domain.exception_request.exception_request import ExceptionRequest, ExceptionRequestStatus
from domain.identity.permission import Permission

router = APIRouter(prefix="/exception-requests", tags=["Signalements"])


class UpdateStatusBody(BaseModel):
    status: ExceptionRequestStatus = Field(
        ...,
        description=(
            "Nouveau statut du signalement : "
            "`acknowledged` (pris en compte), "
            "`resolved` (résolu), "
            "`escalated` (remonté en hiérarchie)."
        ),
    )


def _exc_dict(e: ExceptionRequest) -> dict[str, object]:
    return {
        "id": str(e.id),
        "mission_id": str(e.mission_id),
        "author_user_id": str(e.author_user_id),
        "created_at": e.created_at.isoformat(),
        "status": e.status.value,
        "message": e.message,
        "assigned_to_user_id": str(e.assigned_to_user_id) if e.assigned_to_user_id else None,
        "internal_comment": e.internal_comment,
        "sla_due_at": e.sla_due_at.isoformat() if e.sla_due_at else None,
        "attachment_url": e.attachment_url,
    }


# ---------------------------------------------------------------------------
# GET /exception-requests — File de supervision
# ---------------------------------------------------------------------------
@router.get(
    "",
    dependencies=[Depends(RequirePermissionDep(Permission.EXCEPTION_READ))],
    summary="File de supervision — tous les signalements",
    description="""
**Rôle :** Retourne la liste de tous les signalements terrain, filtrables par statut. Constitue la file de supervision V1 permettant aux responsables hiérarchiques de traiter les blocages signalés par les inspecteurs.

**Paramètre de requête (optionnel) :**
- `status` : Filtre par statut parmi `new`, `acknowledged`, `resolved`, `escalated`.

**Workflow nominal :**
1. Le superviseur consulte la file sans filtre → tous les signalements en attente apparaissent.
2. Il peut filtrer sur `status=new` pour voir uniquement les signalements non traités.
3. Pour chaque signalement, il consulte le détail (`GET /exception-requests/{id}`) puis met à jour le statut (`PATCH /exception-requests/{id}/status`).

**Cas alternatifs :**
- Filtre `status=escalated` → signalements remontés à l'échelon supérieur.
- Sans filtre → tous les statuts confondus (utile pour export ou audit).

**Cas d'exception :**
- `422` : Valeur de `status` inconnue.
""",
)
async def list_exception_requests(
    uow: UoW,
    _user: UserId,
    pagination: PageParams = Depends(),
    status: str | None = Query(
        default=None,
        description="Filtre par statut : new | acknowledged | resolved | escalated.",
    ),
    mission_id: UUID | None = Query(default=None, description="Signalements liés à cette mission."),
    author_user_id: UUID | None = Query(default=None, description="Auteur du signalement."),
    assigned_to_user_id: UUID | None = Query(
        default=None, description="Assigné à cet utilisateur (ignoré si unassigned_only)."
    ),
    unassigned_only: bool = Query(
        default=False, description="Si vrai, uniquement les signalements sans assignation."
    ),
    created_from: datetime | None = Query(
        default=None, description="Créés à partir de cette date (inclus)."
    ),
    created_to: datetime | None = Query(default=None, description="Créés jusqu'à cette date (inclus)."),
    message_q: str | None = Query(
        default=None, description="Recherche insensible à la casse dans le texte du message."
    ),
) -> Page[dict[str, object]]:
    assert uow.exception_requests is not None
    items, total = await uow.exception_requests.list_page(
        pagination.skip,
        pagination.limit,
        status=status,
        mission_id=mission_id,
        author_user_id=author_user_id,
        assigned_to_user_id=assigned_to_user_id,
        unassigned_only=unassigned_only,
        created_from=created_from,
        created_to=created_to,
        message_q=message_q,
    )
    return Page(
        items=[_exc_dict(e) for e in items],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


# ---------------------------------------------------------------------------
# GET /exception-requests/summary — Synthèse (répartition par statut)
# ---------------------------------------------------------------------------
@router.get(
    "/summary",
    dependencies=[Depends(RequirePermissionDep(Permission.EXCEPTION_READ))],
    summary="Synthèse signalements (total et statuts)",
    description="""
Même périmètre que la liste sur mission, auteur, assignation, plage de dates et recherche message,
sans le filtre `status` : total et répartition par statut.
""",
)
async def exception_requests_summary(
    uow: UoW,
    _user: UserId,
    mission_id: UUID | None = Query(default=None),
    author_user_id: UUID | None = Query(default=None),
    assigned_to_user_id: UUID | None = Query(default=None),
    unassigned_only: bool = Query(default=False),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    message_q: str | None = Query(default=None),
) -> dict[str, object]:
    assert uow.exception_requests is not None
    by_status = await uow.exception_requests.count_by_status(
        mission_id=mission_id,
        author_user_id=author_user_id,
        assigned_to_user_id=assigned_to_user_id,
        unassigned_only=unassigned_only,
        created_from=created_from,
        created_to=created_to,
        message_q=message_q,
    )
    total = sum(by_status.values())
    return {"total": total, "by_status": by_status}


# ---------------------------------------------------------------------------
# GET /exception-requests/{id} — Détail
# ---------------------------------------------------------------------------
@router.get(
    "/{exception_id}",
    dependencies=[Depends(RequirePermissionDep(Permission.EXCEPTION_READ))],
    summary="Détail d'un signalement",
    description="""
**Rôle :** Retourne le détail complet d'un signalement : mission concernée, auteur, date, statut actuel et message de description du problème.

**Paramètre de chemin :**
- `exception_id` : UUID du signalement.

**Workflow nominal :**
1. Le superviseur accède au détail à partir de la liste.
2. Il lit le message pour comprendre le blocage signalé.
3. Il effectue ensuite une action corrective (correction du périmètre, contact terrain, etc.) puis met à jour le statut.

**Cas d'exception :**
- `404` : Signalement introuvable (`NOT_FOUND`).
""",
)
async def get_exception_request(
    exception_id: UUID = Path(..., description="UUID du signalement."),
    uow: UoW = ...,
    _user: UserId = ...,
) -> dict[str, object]:
    assert uow.exception_requests is not None
    exc = await uow.exception_requests.get_by_id(exception_id)
    if exc is None:
        raise NotFound("Signalement introuvable.")
    return _exc_dict(exc)


# ---------------------------------------------------------------------------
# PATCH /exception-requests/{id}/status — Mettre à jour le statut
# ---------------------------------------------------------------------------
@router.patch(
    "/{exception_id}/status",
    dependencies=[Depends(RequirePermissionDep(Permission.EXCEPTION_UPDATE_STATUS))],
    summary="Mettre à jour le statut d'un signalement",
    description="""
**Rôle :** Permet au superviseur de faire progresser un signalement dans le mini-workflow V1 : `new` → `acknowledged` → `resolved` ou `escalated`. Garantit que chaque signalement terrain est pris en charge et ne reste pas dans un « trou noir ».

**Paramètre de chemin :**
- `exception_id` : UUID du signalement à mettre à jour.

**Paramètre du corps :**
- `status` : Nouveau statut cible.
  - `acknowledged` : Le superviseur a pris connaissance du signalement.
  - `resolved` : Le problème est résolu (périmètre corrigé, accord terrain obtenu, etc.).
  - `escalated` : Le signalement est remonté à l'échelon hiérarchique supérieur pour arbitrage.

**Workflow nominal :**
1. Le superviseur consulte la file (`GET /exception-requests?status=new`).
2. Il lit le détail du signalement.
3. Il passe le statut à `acknowledged` pour indiquer qu'il a pris en charge.
4. Après action corrective, il passe à `resolved` (ou `escalated` si l'arbitrage est nécessaire).

**Workflow — escalade :**
1. Le superviseur de premier niveau ne peut pas trancher (litige terrain/SIGIS).
2. Il passe le signalement à `escalated`.
3. L'échelon supérieur (ex. délégué régional) voit les signalements escaladés et arbitre.
4. Il repasse à `resolved` une fois l'arbitrage conclu.

**Cas alternatifs :**
- Le statut peut être repassé à `acknowledged` depuis `escalated` si l'arbitrage redescend.
- Aucune contrainte de transition imposée en V1 (à renforcer en V2 avec workflow complet).

**Cas d'exception :**
- `404` : Signalement introuvable.
- `422` : Valeur de statut inconnue.
""",
)
async def update_exception_status(
    exception_id: UUID = Path(..., description="UUID du signalement à mettre à jour."),
    body: UpdateStatusBody = ...,
    uow: UoW = ...,
    _user: UserId = ...,
) -> dict[str, object]:
    assert uow.exception_requests is not None
    exc = await uow.exception_requests.get_by_id(exception_id)
    if exc is None:
        raise NotFound("Signalement introuvable.")
    await uow.exception_requests.update_status(exception_id, body.status)
    return {"id": str(exception_id), "status": body.status.value}


# ---------------------------------------------------------------------------
# PATCH /exception-requests/{id} — Assignation, SLA, commentaire interne
# ---------------------------------------------------------------------------
@router.patch(
    "/{exception_id}",
    dependencies=[Depends(RequirePermissionDep(Permission.EXCEPTION_MANAGE))],
    summary="Mettre à jour un signalement (assignation, SLA, commentaire)",
)
async def patch_exception_request(
    exception_id: UUID = Path(...),
    body: PatchExceptionBody = ...,
    uow: UoW = ...,
    user: UserId = ...,
    request: Request = ...,
) -> dict[str, object]:
    assert uow.exception_requests is not None
    exc = await uow.exception_requests.get_by_id(exception_id)
    if exc is None:
        raise NotFound("Signalement introuvable.")
    if body.status is not None:
        exc.status = body.status
    if body.assigned_to_user_id is not None:
        exc.assigned_to_user_id = body.assigned_to_user_id
    if body.internal_comment is not None:
        exc.internal_comment = body.internal_comment
    if body.sla_due_at is not None:
        exc.sla_due_at = body.sla_due_at
    elif body.status == ExceptionRequestStatus.ACKNOWLEDGED and exc.sla_due_at is None:
        exc.sla_due_at = datetime.now(UTC) + timedelta(hours=72)
    if body.attachment_url is not None:
        exc.attachment_url = body.attachment_url
    await uow.exception_requests.update(exc)
    rid = getattr(request.state, "request_id", None)
    await write_audit(
        uow,
        actor_user_id=user,
        action="exception.patch",
        resource_type="exception_request",
        resource_id=exception_id,
        payload={"status": exc.status.value},
        request_id=rid,
    )
    return _exc_dict(exc)
