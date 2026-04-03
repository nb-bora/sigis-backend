"""Routes Signalements — mini-workflow supervision V1."""

from uuid import UUID

from fastapi import APIRouter, Path, Query
from pydantic import BaseModel, Field

from api.deps import UoW, UserId
from domain.errors import NotFound
from domain.exception_request.exception_request import ExceptionRequest, ExceptionRequestStatus

router = APIRouter(prefix="/exception-requests", tags=["exception-requests"])


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
    }


# ---------------------------------------------------------------------------
# GET /exception-requests — File de supervision
# ---------------------------------------------------------------------------
@router.get(
    "",
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
    status: str | None = Query(
        default=None,
        description="Filtre par statut : new | acknowledged | resolved | escalated.",
    ),
) -> list[dict[str, object]]:
    assert uow.exception_requests is not None
    items = await uow.exception_requests.list_all(status=status)
    return [_exc_dict(e) for e in items]


# ---------------------------------------------------------------------------
# GET /exception-requests/{id} — Détail
# ---------------------------------------------------------------------------
@router.get(
    "/{exception_id}",
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
