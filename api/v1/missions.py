"""Routes Missions — planification et suivi V1."""

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query

from api.deps import RequirePermissionDep, UoW, UserId
from api.v1.schemas import CreateMissionBody, ExceptionBody, UpdateMissionBody
from application.use_cases.create_exception_request import (
    CreateExceptionCommand,
    CreateExceptionRequest,
)
from application.use_cases.create_mission import CreateMission, CreateMissionCommand
from domain.errors import Conflict, NotFound
from domain.exception_request.exception_request import ExceptionRequest
from domain.identity.permission import Permission
from domain.mission.mission import Mission, MissionStatus
from domain.site_visit.site_visit import SiteVisit

router = APIRouter(prefix="/missions", tags=["Missions"])


# ---------------------------------------------------------------------------
# POST /missions — Créer
# ---------------------------------------------------------------------------
@router.post(
    "",
    dependencies=[Depends(RequirePermissionDep(Permission.MISSION_CREATE))],
    summary="Créer une mission",
    description="""
**Rôle :** Planifie une nouvelle mission d'inspection : associe un inspecteur à un établissement sur une fenêtre horaire.

**Paramètres du corps :**
- `establishment_id` : UUID de l'établissement à inspecter (doit exister).
- `inspector_id` : UUID de l'inspecteur assigné (créé automatiquement s'il est inconnu en V1).
- `window_start` / `window_end` : Fenêtre horaire autorisée pour le check-in (ISO 8601 avec timezone recommandée).
- `sms_code` : Code SMS optionnel pour le mode de validation C (SMS_SHORTCODE).

**Workflow nominal :**
1. Le serveur vérifie l'existence de l'établissement.
2. Il s'assure que l'inspecteur existe (ou le crée en V1 dev).
3. Il génère un `host_token` UUID aléatoire (utilisé pour le QR code mode B).
4. La mission est créée au statut `planned` et son identifiant est retourné.

**Cas alternatifs :**
- Si `sms_code` non fourni, le mode SMS (C) ne sera pas utilisable pour cette mission.
- La `window_start` dans le passé est acceptée (utile pour les tests et rattrapages).

**Cas d'exception :**
- `404` : L'établissement n'existe pas (`NOT_FOUND`).
- `422` : Corps invalide (champ manquant, UUID malformé).
""",
)
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


# ---------------------------------------------------------------------------
# GET /missions — Lister
# ---------------------------------------------------------------------------
@router.get(
    "",
    dependencies=[Depends(RequirePermissionDep(Permission.MISSION_READ))],
    summary="Lister les missions",
    description="""
**Rôle :** Retourne la liste des missions, avec filtres optionnels. Utilisée par la supervision pour le suivi et les KPI d'adoption.

**Paramètres de requête (tous optionnels) :**
- `inspector_id` : Filtre les missions d'un inspecteur spécifique.
- `establishment_id` : Filtre les missions d'un établissement spécifique.
- `status` : Filtre par statut parmi `planned`, `in_progress`, `completed`, `cancelled`.

**Workflow nominal :**
1. Le serveur applique les filtres fournis (aucun filtre = toutes les missions).
2. Il retourne la liste ordonnée par ordre d'insertion.

**Cas alternatifs :**
- Aucun filtre → retourne toutes les missions (peut être large en production : paginer en V2).
- Combinaison de filtres possible (ex. `inspector_id` + `status=planned`).

**Cas d'exception :**
- `422` : UUID invalide dans un paramètre de filtre.
""",
)
async def list_missions(
    uow: UoW,
    _user: UserId,
    inspector_id: UUID | None = Query(default=None, description="Filtre par UUID de l'inspecteur."),
    establishment_id: UUID | None = Query(
        default=None, description="Filtre par UUID de l'établissement."
    ),
    status: str | None = Query(
        default=None,
        description="Filtre par statut : planned | in_progress | completed | cancelled.",
    ),
) -> list[dict[str, object]]:
    assert uow.missions is not None
    items = await uow.missions.list_all(
        inspector_id=inspector_id,
        establishment_id=establishment_id,
        status=status,
    )
    return [_mission_dict(m) for m in items]


# ---------------------------------------------------------------------------
# GET /missions/{id} — Détail
# ---------------------------------------------------------------------------
@router.get(
    "/{mission_id}",
    dependencies=[Depends(RequirePermissionDep(Permission.MISSION_READ))],
    summary="Détail d'une mission",
    description="""
**Rôle :** Retourne toutes les informations d'une mission identifiée par son UUID, incluant son statut courant, la fenêtre horaire et le `host_token` pour le QR code.

**Paramètre de chemin :**
- `mission_id` : UUID de la mission.

**Workflow nominal :**
1. Le serveur charge la mission.
2. Il retourne ses attributs complets (établissement, inspecteur, fenêtre, statut, host_token).

**Cas d'exception :**
- `404` : Mission introuvable (`NOT_FOUND`).
- `422` : Format UUID invalide.
""",
)
async def get_mission(
    mission_id: UUID = Path(..., description="UUID de la mission."),
    uow: UoW = ...,
    _user: UserId = ...,
) -> dict[str, object]:
    assert uow.missions is not None
    mission = await uow.missions.get_by_id(mission_id)
    if mission is None:
        raise NotFound("Mission introuvable.")
    return _mission_dict(mission)


# ---------------------------------------------------------------------------
# PATCH /missions/{id} — Modifier
# ---------------------------------------------------------------------------
@router.patch(
    "/{mission_id}",
    dependencies=[Depends(RequirePermissionDep(Permission.MISSION_UPDATE))],
    summary="Modifier une mission",
    description="""
**Rôle :** Met à jour partiellement une mission existante. Permet de reporter la fenêtre horaire, d'annuler une mission ou de changer le code SMS.

**Paramètre de chemin :**
- `mission_id` : UUID de la mission à modifier.

**Paramètres du corps (tous optionnels) :**
- `window_start` / `window_end` : Nouveau créneau horaire (report de mission).
- `status` : Nouveau statut — utiliser `cancelled` pour annuler, `completed` pour clôturer manuellement.
- `sms_code` : Mise à jour du code SMS pour le mode de validation C.

**Workflow nominal :**
1. Le serveur charge la mission existante.
2. Il applique uniquement les champs fournis.
3. Les modifications sont persistées et la mission mise à jour est retournée.

**Cas alternatifs :**
- Report de mission : fournir `window_start` + `window_end` uniquement.
- Annulation : fournir `status: "cancelled"` uniquement.

**Cas d'exception :**
- `404` : Mission introuvable (`NOT_FOUND`).
- `409` : Tentative de modifier une mission déjà `completed` vers un statut incompatible — validation à renforcer en V2.
- `422` : Valeur de statut inconnue ou fenêtre invalide.
""",
)
async def update_mission(
    mission_id: UUID = Path(..., description="UUID de la mission à modifier."),
    body: UpdateMissionBody = ...,
    uow: UoW = ...,
    _user: UserId = ...,
) -> dict[str, object]:
    assert uow.missions is not None
    mission = await uow.missions.get_by_id(mission_id)
    if mission is None:
        raise NotFound("Mission introuvable.")

    if body.window_start is not None:
        mission.window_start = body.window_start
    if body.window_end is not None:
        mission.window_end = body.window_end
    if body.status is not None:
        try:
            mission.status = MissionStatus(body.status)
        except ValueError:
            raise Conflict(f"Statut inconnu : {body.status}.")
    if body.sms_code is not None:
        mission.sms_code = body.sms_code

    await uow.missions.update(mission)
    return _mission_dict(mission)


# ---------------------------------------------------------------------------
# GET /missions/{id}/site-visit — Visite associée
# ---------------------------------------------------------------------------
@router.get(
    "/{mission_id}/site-visit",
    dependencies=[Depends(RequirePermissionDep(Permission.VISIT_READ))],
    summary="Visite terrain d'une mission",
    description="""
**Rôle :** Retourne la visite terrain (`SiteVisit`) associée à une mission. Une visite est créée lors du premier check-in de l'inspecteur.

**Paramètre de chemin :**
- `mission_id` : UUID de la mission.

**Workflow nominal :**
1. Le serveur vérifie que la mission existe.
2. Il recherche la visite liée à cette mission (relation 1:1 en V1).
3. Il retourne le statut de la visite, les horodatages et les positions GPS enregistrées.

**Cas alternatifs :**
- Si le check-in n'a pas encore eu lieu, aucune visite n'existe → `404`.

**Cas d'exception :**
- `404` : Mission introuvable ou aucune visite démarrée.
""",
)
async def get_mission_site_visit(
    mission_id: UUID = Path(..., description="UUID de la mission."),
    uow: UoW = ...,
    _user: UserId = ...,
) -> dict[str, object]:
    assert uow.missions is not None
    assert uow.site_visits is not None
    mission = await uow.missions.get_by_id(mission_id)
    if mission is None:
        raise NotFound("Mission introuvable.")
    visit = await uow.site_visits.get_by_mission_id(mission_id)
    if visit is None:
        raise NotFound("Aucune visite démarrée pour cette mission.")
    return _site_visit_dict(visit)


# ---------------------------------------------------------------------------
# GET /missions/{id}/exception-requests — Signalements
# ---------------------------------------------------------------------------
@router.get(
    "/{mission_id}/exception-requests",
    dependencies=[Depends(RequirePermissionDep(Permission.EXCEPTION_READ))],
    summary="Signalements d'une mission",
    description="""
**Rôle :** Retourne la liste de tous les signalements (périmètre incorrect, établissement fermé, absent, etc.) rattachés à une mission donnée.

**Paramètre de chemin :**
- `mission_id` : UUID de la mission.

**Workflow nominal :**
1. Le serveur vérifie l'existence de la mission.
2. Il retourne tous les signalements liés, ordonnés par date de création.

**Cas alternatifs :**
- Aucun signalement → retourne une liste vide `[]`.

**Cas d'exception :**
- `404` : Mission introuvable.
""",
)
async def list_mission_exceptions(
    mission_id: UUID = Path(..., description="UUID de la mission."),
    uow: UoW = ...,
    _user: UserId = ...,
) -> list[dict[str, object]]:
    assert uow.missions is not None
    assert uow.exception_requests is not None
    mission = await uow.missions.get_by_id(mission_id)
    if mission is None:
        raise NotFound("Mission introuvable.")
    items = await uow.exception_requests.list_by_mission_id(mission_id)
    return [_exception_dict(e) for e in items]


# ---------------------------------------------------------------------------
# POST /missions/{id}/exception-requests — Créer signalement
# ---------------------------------------------------------------------------
@router.post(
    "/{mission_id}/exception-requests",
    dependencies=[Depends(RequirePermissionDep(Permission.EXCEPTION_CREATE))],
    summary="Créer un signalement",
    description="""
**Rôle :** Permet à un inspecteur ou un responsable de signaler un problème bloquant lors d'une mission (périmètre géographique incorrect, établissement fermé, responsable absent, etc.). Garantit qu'aucune situation de blocage ne reste dans un « trou noir ».

**Paramètre de chemin :**
- `mission_id` : UUID de la mission concernée.

**Paramètre du corps :**
- `message` : Description du problème (1 à 4 000 caractères).

**Workflow nominal :**
1. Le serveur vérifie que la mission existe.
2. Il crée le signalement au statut `new` avec l'auteur identifié par `X-User-Id`.
3. Le signalement rejoint la file de supervision, visible par les responsables hiérarchiques.
4. L'identifiant du signalement est retourné.

**Cas alternatifs :**
- Plusieurs signalements peuvent être créés sur la même mission (ex. périmètre faux + responsable absent).

**Cas d'exception :**
- `404` : Mission introuvable.
- `422` : Message vide ou dépassant 4 000 caractères.
""",
)
async def create_exception(
    mission_id: UUID = Path(..., description="UUID de la mission concernée."),
    body: ExceptionBody = ...,
    uow: UoW = ...,
    user: UserId = ...,
) -> dict[str, object]:
    uc = CreateExceptionRequest(uow)
    return await uc.execute(
        CreateExceptionCommand(
            mission_id=mission_id,
            author_user_id=user,
            message=body.message,
        )
    )


# ---------------------------------------------------------------------------
# Sérialisation
# ---------------------------------------------------------------------------
def _mission_dict(m: Mission) -> dict[str, object]:
    return {
        "id": str(m.id),
        "establishment_id": str(m.establishment_id),
        "inspector_id": str(m.inspector_id),
        "window_start": m.window_start.isoformat(),
        "window_end": m.window_end.isoformat(),
        "status": m.status.value,
        "host_token": str(m.host_token) if m.host_token else None,
    }


def _site_visit_dict(v: SiteVisit) -> dict[str, object]:
    return {
        "id": str(v.id),
        "mission_id": str(v.mission_id),
        "status": v.status.value,
        "host_validation_mode": v.host_validation_mode.value if v.host_validation_mode else None,
        "checked_in_at": v.checked_in_at.isoformat() if v.checked_in_at else None,
        "checked_out_at": v.checked_out_at.isoformat() if v.checked_out_at else None,
        "inspector_lat": v.inspector_lat,
        "inspector_lon": v.inspector_lon,
        "host_lat": v.host_lat,
        "host_lon": v.host_lon,
    }


def _exception_dict(e: ExceptionRequest) -> dict[str, object]:
    return {
        "id": str(e.id),
        "mission_id": str(e.mission_id),
        "author_user_id": str(e.author_user_id),
        "created_at": e.created_at.isoformat(),
        "status": e.status.value,
        "message": e.message,
    }
