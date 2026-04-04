"""Routes Missions — planification et suivi V1."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request

from api.deps import RequirePermissionDep, SettingsDep, UoW, UserId
from api.v1.schemas import (
    CancelMissionBody,
    CreateMissionBody,
    ExceptionBody,
    ReassignMissionBody,
    SubmitMissionOutcomeBody,
    UpdateMissionBody,
)
from application.use_cases.create_exception_request import (
    CreateExceptionCommand,
    CreateExceptionRequest,
)
from application.use_cases.create_mission import CreateMission, CreateMissionCommand
from application.use_cases.mission_workflow import (
    ApproveMission,
    ApproveMissionCommand,
    CancelMission,
    CancelMissionCommand,
    ReassignInspector,
    ReassignInspectorCommand,
    SubmitMissionOutcome,
    SubmitMissionOutcomeCommand,
)
from common.audit import write_audit
from common.business_notifications import notify_mission_cancelled
from common.host_qr_jwt import create_host_qr_jwt
from common.pagination import Page, PageParams
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
            objective=body.objective,
            plan_reference=body.plan_reference,
            requires_approval=body.requires_approval,
            designated_host_user_id=body.designated_host_user_id,
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
- `window_from` / `window_to` : Plage temporelle — missions dont la fenêtre **intersecte** l'intervalle
  (`window_end >= window_from` et `window_start <= window_to`).

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
    pagination: PageParams = Depends(),
    inspector_id: UUID | None = Query(default=None, description="Filtre par UUID de l'inspecteur."),
    establishment_id: UUID | None = Query(
        default=None, description="Filtre par UUID de l'établissement."
    ),
    status: str | None = Query(
        default=None,
        description="Filtre par statut : draft | planned | in_progress | completed | cancelled.",
    ),
    territory_code: str | None = Query(
        default=None, description="Filtre par code territoire de l'établissement."
    ),
    window_from: datetime | None = Query(
        default=None,
        description="Début de plage : garde les missions avec window_end >= cette date.",
    ),
    window_to: datetime | None = Query(
        default=None,
        description="Fin de plage : garde les missions avec window_start <= cette date.",
    ),
) -> Page[dict[str, object]]:
    assert uow.missions is not None
    items, total = await uow.missions.list_page(
        pagination.skip,
        pagination.limit,
        inspector_id=inspector_id,
        establishment_id=establishment_id,
        status=status,
        territory_code=territory_code,
        window_from=window_from,
        window_to=window_to,
    )
    return Page(
        items=[_mission_dict(m) for m in items],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


# ---------------------------------------------------------------------------
# GET /missions/summary — Synthèse (compteurs par statut, sans filtre statut)
# ---------------------------------------------------------------------------
@router.get(
    "/summary",
    dependencies=[Depends(RequirePermissionDep(Permission.MISSION_READ))],
    summary="Synthèse missions (total et répartition par statut)",
    description="""
Même périmètre de filtrage que `GET /missions` (inspecteur, établissement, territoire, plage de dates),
sans le filtre `status` : retourne le total et la répartition par statut pour les missions concernées.
""",
)
async def missions_summary(
    uow: UoW,
    _user: UserId,
    inspector_id: UUID | None = Query(default=None),
    establishment_id: UUID | None = Query(default=None),
    territory_code: str | None = Query(default=None),
    window_from: datetime | None = Query(default=None),
    window_to: datetime | None = Query(default=None),
) -> dict[str, object]:
    assert uow.missions is not None
    by_status = await uow.missions.count_by_status(
        inspector_id=inspector_id,
        establishment_id=establishment_id,
        territory_code=territory_code,
        window_from=window_from,
        window_to=window_to,
    )
    total = sum(by_status.values())
    return {"total": total, "missions_by_status": by_status}


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
    if body.designated_host_user_id is not None:
        mission.designated_host_user_id = body.designated_host_user_id
    if body.objective is not None:
        mission.objective = body.objective
    if body.plan_reference is not None:
        mission.plan_reference = body.plan_reference

    await uow.missions.update(mission)
    return _mission_dict(mission)


# ---------------------------------------------------------------------------
# POST /missions/{id}/approve — Validation hiérarchique (draft → planned)
# ---------------------------------------------------------------------------
@router.post(
    "/{mission_id}/approve",
    dependencies=[Depends(RequirePermissionDep(Permission.MISSION_APPROVE))],
    summary="Valider une mission en brouillon",
)
async def approve_mission(
    mission_id: UUID = Path(...),
    uow: UoW = ...,
    user: UserId = ...,
    request: Request = ...,
) -> dict[str, object]:
    uc = ApproveMission(uow)
    mission = await uc.execute(ApproveMissionCommand(mission_id=mission_id, approver_user_id=user))
    rid = getattr(request.state, "request_id", None)
    await write_audit(
        uow,
        actor_user_id=user,
        action="mission.approve",
        resource_type="mission",
        resource_id=mission_id,
        payload={"status": mission.status.value},
        request_id=rid,
    )
    return _mission_dict(mission)


# ---------------------------------------------------------------------------
# POST /missions/{id}/cancel — Annulation avec motif
# ---------------------------------------------------------------------------
@router.post(
    "/{mission_id}/cancel",
    dependencies=[Depends(RequirePermissionDep(Permission.MISSION_CANCEL))],
    summary="Annuler une mission avec motif",
)
async def cancel_mission_ep(
    mission_id: UUID = Path(...),
    body: CancelMissionBody = ...,
    uow: UoW = ...,
    user: UserId = ...,
    request: Request = ...,
) -> dict[str, object]:
    uc = CancelMission(uow)
    mission = await uc.execute(
        CancelMissionCommand(
            mission_id=mission_id,
            reason=body.reason,
            cancelled_by_user_id=user,
        )
    )
    rid = getattr(request.state, "request_id", None)
    await write_audit(
        uow,
        actor_user_id=user,
        action="mission.cancel",
        resource_type="mission",
        resource_id=mission_id,
        payload={"reason": body.reason[:500]},
        request_id=rid,
    )
    await notify_mission_cancelled(mission_id, body.reason)
    return _mission_dict(mission)


# ---------------------------------------------------------------------------
# POST /missions/{id}/reassign — Réaffectation inspecteur
# ---------------------------------------------------------------------------
@router.post(
    "/{mission_id}/reassign",
    dependencies=[Depends(RequirePermissionDep(Permission.MISSION_REASSIGN))],
    summary="Réaffecter l'inspecteur (nouvelle mission, ancienne annulée)",
)
async def reassign_mission(
    mission_id: UUID = Path(...),
    body: ReassignMissionBody = ...,
    uow: UoW = ...,
    user: UserId = ...,
    request: Request = ...,
) -> dict[str, object]:
    uc = ReassignInspector(uow)
    mission = await uc.execute(
        ReassignInspectorCommand(
            mission_id=mission_id,
            new_inspector_id=body.new_inspector_id,
            actor_user_id=user,
        )
    )
    rid = getattr(request.state, "request_id", None)
    await write_audit(
        uow,
        actor_user_id=user,
        action="mission.reassign",
        resource_type="mission",
        resource_id=mission.id,
        payload={"from_mission_id": str(mission_id), "inspector_id": str(mission.inspector_id)},
        request_id=rid,
    )
    return _mission_dict(mission)


# ---------------------------------------------------------------------------
# POST /missions/{id}/outcome — Rapport de mission
# ---------------------------------------------------------------------------
@router.post(
    "/{mission_id}/outcome",
    dependencies=[Depends(RequirePermissionDep(Permission.MISSION_OUTCOME_WRITE))],
    summary="Soumettre le rapport de mission (MissionOutcome)",
)
async def post_mission_outcome(
    mission_id: UUID = Path(...),
    body: SubmitMissionOutcomeBody = ...,
    uow: UoW = ...,
    user: UserId = ...,
    request: Request = ...,
) -> dict[str, object]:
    uc = SubmitMissionOutcome(uow)
    outcome = await uc.execute(
        SubmitMissionOutcomeCommand(
            mission_id=mission_id,
            summary=body.summary,
            notes=body.notes,
            compliance_level=body.compliance_level,
            author_user_id=user,
        )
    )
    rid = getattr(request.state, "request_id", None)
    await write_audit(
        uow,
        actor_user_id=user,
        action="mission.outcome",
        resource_type="mission",
        resource_id=mission_id,
        payload={"outcome_id": str(outcome.id)},
        request_id=rid,
    )
    return {
        "id": str(outcome.id),
        "mission_id": str(outcome.mission_id),
        "summary": outcome.summary,
        "notes": outcome.notes,
        "compliance_level": outcome.compliance_level,
        "created_at": outcome.created_at.isoformat(),
        "created_by_user_id": str(outcome.created_by_user_id),
    }


# ---------------------------------------------------------------------------
# GET /missions/{id}/outcome — Détail rapport
# ---------------------------------------------------------------------------
@router.get(
    "/{mission_id}/outcome",
    dependencies=[Depends(RequirePermissionDep(Permission.MISSION_READ))],
    summary="Lire le rapport de mission",
)
async def get_mission_outcome(
    mission_id: UUID = Path(...),
    uow: UoW = ...,
    _user: UserId = ...,
) -> dict[str, object]:
    assert uow.mission_outcomes is not None
    o = await uow.mission_outcomes.get_by_mission_id(mission_id)
    if o is None:
        raise NotFound("Aucun rapport pour cette mission.")
    return {
        "id": str(o.id),
        "mission_id": str(o.mission_id),
        "summary": o.summary,
        "notes": o.notes,
        "compliance_level": o.compliance_level,
        "created_at": o.created_at.isoformat(),
        "created_by_user_id": str(o.created_by_user_id),
    }


# ---------------------------------------------------------------------------
# GET /missions/{id}/host-qr-jwt — JWT court pour QR dynamique
# ---------------------------------------------------------------------------
@router.get(
    "/{mission_id}/host-qr-jwt",
    dependencies=[Depends(RequirePermissionDep(Permission.MISSION_READ))],
    summary="Obtenir un JWT court pour QR hôte (mode B renforcé)",
)
async def get_host_qr_jwt(
    mission_id: UUID = Path(...),
    uow: UoW = ...,
    settings: SettingsDep = ...,
    _user: UserId = ...,
) -> dict[str, object]:
    assert uow.missions is not None
    mission = await uow.missions.get_by_id(mission_id)
    if mission is None:
        raise NotFound("Mission introuvable.")
    if settings.host_qr_jwt_ttl_minutes <= 0:
        raise Conflict("Émission JWT QR désactivée (SIGIS_HOST_QR_JWT_TTL_MINUTES=0).")
    token = create_host_qr_jwt(
        secret_key=settings.secret_key,
        algorithm=settings.jwt_algorithm,
        ttl_minutes=settings.host_qr_jwt_ttl_minutes,
        mission=mission,
    )
    return {"host_qr_jwt": token, "expires_in_minutes": settings.host_qr_jwt_ttl_minutes}


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
        "sms_code": m.sms_code,
        "designated_host_user_id": str(m.designated_host_user_id)
        if m.designated_host_user_id
        else None,
        "objective": m.objective,
        "plan_reference": m.plan_reference,
        "requires_approval": m.requires_approval,
        "cancellation_reason": m.cancellation_reason,
        "cancelled_at": m.cancelled_at.isoformat() if m.cancelled_at else None,
        "cancelled_by_user_id": str(m.cancelled_by_user_id) if m.cancelled_by_user_id else None,
        "previous_mission_id": str(m.previous_mission_id) if m.previous_mission_id else None,
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
        "assigned_to_user_id": str(e.assigned_to_user_id) if e.assigned_to_user_id else None,
        "internal_comment": e.internal_comment,
        "sla_due_at": e.sla_due_at.isoformat() if e.sla_due_at else None,
        "attachment_url": e.attachment_url,
    }
