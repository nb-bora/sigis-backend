"""Routes Visites terrain — exécution terrain V1 (check-in, validation hôte, check-out)."""

from uuid import UUID

from fastapi import APIRouter, Path

from api.deps import UoW, UserId
from api.v1.schemas import CheckInBody, CheckOutBody, ConfirmHostBody
from application.use_cases.check_in_inspector import CheckInInspector, CheckInInspectorCommand
from application.use_cases.check_out_visit import CheckOutCommand, CheckOutVisit
from application.use_cases.confirm_host_presence import ConfirmHostCommand, ConfirmHostPresence
from domain.errors import NotFound
from domain.site_visit.site_visit import SiteVisit

router = APIRouter(tags=["site-visits"])


# ---------------------------------------------------------------------------
# GET /site-visits/{id} — Détail
# ---------------------------------------------------------------------------
@router.get(
    "/site-visits/{site_visit_id}",
    summary="Détail d'une visite terrain",
    description="""
**Rôle :** Retourne l'état complet d'une visite terrain identifiée par son UUID : statut, mode de validation, horodatages et positions GPS enregistrées.

**Paramètre de chemin :**
- `site_visit_id` : UUID de la visite (retourné lors du check-in).

**Workflow nominal :**
1. Le serveur charge la visite par son identifiant.
2. Il retourne tous les attributs : statut actuel, mode de validation hôte, `checked_in_at`, `checked_out_at`, positions de l'inspecteur et du responsable (si mode A).

**Champs de statut possibles :**
- `scheduled` → `pending_host_validation` → `copresence_validated` → `completed`
- `cancelled` : visite annulée.

**Cas d'exception :**
- `404` : Visite introuvable (`NOT_FOUND`).
""",
)
async def get_site_visit(
    site_visit_id: UUID = Path(..., description="UUID de la visite terrain."),
    uow: UoW = ...,
    _user: UserId = ...,
) -> dict[str, object]:
    assert uow.site_visits is not None
    visit = await uow.site_visits.get_by_id(site_visit_id)
    if visit is None:
        raise NotFound("Visite introuvable.")
    return _site_visit_dict(visit)


# ---------------------------------------------------------------------------
# POST /missions/{id}/check-in — Check-in inspecteur
# ---------------------------------------------------------------------------
@router.post(
    "/missions/{mission_id}/check-in",
    summary="Check-in de l'inspecteur",
    description="""
**Rôle :** Enregistre l'arrivée de l'inspecteur sur le site. Vérifie que la position GPS est dans la zone autorisée et que la mission est en cours de fenêtre horaire. Crée la visite terrain et attend la validation du responsable.

**Paramètre de chemin :**
- `mission_id` : UUID de la mission pour laquelle l'inspecteur effectue son check-in.

**Paramètres du corps :**
- `latitude` / `longitude` : Position GPS de l'inspecteur au moment du check-in.
- `client_request_id` : Clé d'idempotence — permet de rejouer la requête sans créer un double check-in (mode offline).
- `host_validation_mode` : Mode de validation choisi pour cette visite (`app_gps`, `qr_static`, `sms_shortcode`).

**Workflow nominal :**
1. Vérification de l'idempotence : si `client_request_id` déjà connu, retourne la réponse cachée.
2. Chargement de la mission et de l'établissement associé.
3. Vérification que l'inspecteur est bien assigné à la mission.
4. Vérification que l'heure courante est dans la fenêtre (`window_start` ≤ maintenant ≤ `window_end`).
5. Calcul de la distance (haversine) entre la position et le centre de l'établissement.
6. Application des seuils de géofence → statut `OK` (confirmée), `APPROXIMATE` (probable) ou `REJECTED` (hors zone).
7. Si `REJECTED` : erreur `OUTSIDE_GEOFENCE` — l'inspecteur doit créer un signalement.
8. Si `OK` ou `APPROXIMATE` : création de la visite au statut `pending_host_validation`, enregistrement de la `PresenceProof` inspecteur.
9. La réponse est mise en cache pour idempotence.

**Cas alternatifs :**
- `APPROXIMATE` : check-in accepté mais le statut indique une précision GPS réduite — visible dans les logs.
- Offline : l'application mobile rejoue la requête avec le même `client_request_id` à la reconnexion → réponse identique.

**Cas d'exception :**
- `400 OUTSIDE_GEOFENCE` : Position hors de la zone élargie.
- `400 MISSION_EXPIRED` : Heure hors de la fenêtre autorisée.
- `403 FORBIDDEN` : L'inspecteur n'est pas assigné à cette mission.
- `404 NOT_FOUND` : Mission ou établissement introuvable.
- `409 CONFLICT` : Une visite est déjà en cours pour cette mission.
""",
)
async def check_in(
    mission_id: UUID = Path(..., description="UUID de la mission."),
    body: CheckInBody = ...,
    uow: UoW = ...,
    user: UserId = ...,
) -> dict[str, object]:
    uc = CheckInInspector(uow)
    return await uc.execute(
        CheckInInspectorCommand(
            mission_id=mission_id,
            inspector_user_id=user,
            latitude=body.latitude,
            longitude=body.longitude,
            client_request_id=body.client_request_id,
            host_validation_mode=body.host_validation_mode,
        )
    )


# ---------------------------------------------------------------------------
# POST /site-visits/{id}/host-confirmation — Validation hôte
# ---------------------------------------------------------------------------
@router.post(
    "/site-visits/{site_visit_id}/host-confirmation",
    summary="Validation de présence par le responsable (hôte)",
    description="""
**Rôle :** Enregistre la confirmation de présence par le responsable d'établissement. Constitue la deuxième moitié de la co-présence. Le comportement dépend du mode de validation choisi lors du check-in.

**Paramètre de chemin :**
- `site_visit_id` : UUID de la visite créée lors du check-in.

**Paramètres du corps :**
- `mission_id` : UUID de la mission (cohérence croisée).
- `client_request_id` : Clé d'idempotence.
- `latitude` / `longitude` : Position GPS du responsable. **Requis uniquement en mode `app_gps`.**
- `qr_token` : UUID extrait du QR code affiché dans l'établissement. **Requis en mode `qr_static`.**
- `sms_code` : Code reçu par SMS. **Requis en mode `sms_shortcode`.**

**Workflow — Mode A (app_gps) :**
1. Vérification idempotence.
2. Chargement de la visite et de la mission.
3. Calcul de la distance entre la position de l'inspecteur (au check-in) et celle du responsable.
4. Vérification : délai ≤ 15 min depuis le check-in ET distance mutuelle ≤ 100 m.
5. Co-présence validée → visite passe à `copresence_validated`, `CoPresenceEvent` enregistré.

**Workflow — Mode B (qr_static) :**
1. Le jeton UUID fourni est comparé au `host_token` de la mission.
2. Vérification que l'heure est dans la fenêtre mission.
3. Validation acceptée si jeton correct et fenêtre active.

**Workflow — Mode C (sms_shortcode) :**
1. Le code SMS fourni est comparé au `sms_code` de la mission.
2. Vérification que l'heure est dans la fenêtre mission.
3. Validation acceptée si code correct et fenêtre active.

**Cas d'exception :**
- `400 COPRESENCE_TIMEOUT` : Délai de 15 min dépassé (mode A).
- `400 COPRESENCE_DISTANCE` : Distance mutuelle > 100 m (mode A).
- `400 INVALID_QR_TOKEN` : Jeton QR incorrect (mode B).
- `400 INVALID_SMS_CODE` : Code SMS incorrect (mode C).
- `400 SMS_NOT_CONFIGURED` : Aucun code SMS défini pour cette mission (mode C).
- `400 MISSION_EXPIRED` : Heure hors fenêtre mission (modes B et C).
- `404 NOT_FOUND` : Visite ou mission introuvable.
- `409 CONFLICT` : Mode de validation non défini, ou position manquante pour le mode A.
""",
)
async def confirm_host(
    site_visit_id: UUID = Path(..., description="UUID de la visite terrain."),
    body: ConfirmHostBody = ...,
    uow: UoW = ...,
    user: UserId = ...,
) -> dict[str, object]:
    uc = ConfirmHostPresence(uow)
    return await uc.execute(
        ConfirmHostCommand(
            site_visit_id=site_visit_id,
            mission_id=body.mission_id,
            host_user_id=user,
            client_request_id=body.client_request_id,
            latitude=body.latitude,
            longitude=body.longitude,
            qr_token=body.qr_token,
            sms_code=body.sms_code,
        )
    )


# ---------------------------------------------------------------------------
# POST /site-visits/{id}/check-out — Check-out
# ---------------------------------------------------------------------------
@router.post(
    "/site-visits/{site_visit_id}/check-out",
    summary="Check-out de l'inspecteur",
    description="""
**Rôle :** Clôture la visite terrain. Calcule la durée de présence (`checked_out_at - checked_in_at`) et marque la visite `completed`. La co-présence doit avoir été validée au préalable.

**Paramètre de chemin :**
- `site_visit_id` : UUID de la visite terrain.

**Paramètres du corps :**
- `mission_id` : UUID de la mission (cohérence croisée).
- `client_request_id` : Clé d'idempotence — évite un double check-out en cas de rejeu offline.

**Workflow nominal :**
1. Vérification idempotence.
2. Vérification que l'inspecteur connecté est bien l'assigné de la mission.
3. Vérification que la visite est au statut `copresence_validated` (pré-requis obligatoire).
4. Enregistrement de `checked_out_at` (horodatage serveur UTC).
5. Calcul de la durée en secondes : `checked_out_at - checked_in_at`.
6. La visite passe au statut `completed`.
7. La réponse (statut, horodatage, durée) est mise en cache.

**Nota bene sur la durée :**
La `presence_duration_seconds` mesure le temps entre le check-in et le check-out. Elle ne représente **pas** la durée pédagogique ni la qualité de l'inspection — c'est une preuve de présence chronométrée.

**Cas alternatifs :**
- Replay offline : même `client_request_id` → retourne la réponse cachée sans recalcul.

**Cas d'exception :**
- `400 INVARIANT_VIOLATION` : Co-présence non encore validée — check-out impossible.
- `400 ALREADY_CHECKED_OUT` : Check-out déjà effectué sur cette visite.
- `403 FORBIDDEN` : L'utilisateur n'est pas l'inspecteur assigné.
- `404 NOT_FOUND` : Visite ou mission introuvable.
- `409 CONFLICT` : Mission incohérente avec la visite.
""",
)
async def check_out_ep(
    site_visit_id: UUID = Path(..., description="UUID de la visite terrain."),
    body: CheckOutBody = ...,
    uow: UoW = ...,
    user: UserId = ...,
) -> dict[str, object]:
    uc = CheckOutVisit(uow)
    return await uc.execute(
        CheckOutCommand(
            site_visit_id=site_visit_id,
            mission_id=body.mission_id,
            inspector_user_id=user,
            client_request_id=body.client_request_id,
        )
    )


# ---------------------------------------------------------------------------
# Sérialisation
# ---------------------------------------------------------------------------
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
