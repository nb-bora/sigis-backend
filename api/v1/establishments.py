"""Routes Établissements — référentiel géographique V1."""

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query

from api.deps import RequirePermissionDep, UoW, UserId
from api.v1.schemas import CreateEstablishmentBody, UpdateEstablishmentBody
from application.use_cases.create_mission import CreateEstablishment, CreateEstablishmentCommand
from common.pagination import Page, PageParams
from domain.errors import NotFound
from domain.identity.permission import Permission

router = APIRouter(prefix="/establishments", tags=["Établissements"])


# ---------------------------------------------------------------------------
# POST /establishments — Créer
# ---------------------------------------------------------------------------
@router.post(
    "",
    dependencies=[Depends(RequirePermissionDep(Permission.ESTABLISHMENT_CREATE))],
    summary="Créer un établissement",
    description="""
**Rôle :** Enregistre un nouvel établissement dans le référentiel géographique SIGIS.

**Paramètres du corps :**
- `name` : Nom officiel de l'établissement (ex. « Lycée de la Cité »).
- `center_lat` / `center_lon` : Coordonnées GPS du centre (WGS-84). Doivent correspondre à une prise de mesure terrain réelle pour éviter les rejets injustes.
- `radius_strict_m` : Rayon nominal en mètres — une position dans ce rayon donne le statut **Présence confirmée**.
- `radius_relaxed_m` : Rayon élargi — une position dans la couronne (entre strict et élargi) donne le statut **Présence probable**. Au-delà : **Hors zone**.

**Workflow nominal :**
1. Le client envoie les informations de l'établissement.
2. Le serveur crée l'établissement avec `geometry_version = 1` et retourne son identifiant UUID.

**Cas alternatifs :**
- Si `radius_relaxed_m < radius_strict_m`, les calculs de géofence peuvent être incohérents — à valider côté client.

**Cas d'exception :**
- `422` : Corps invalide (champ manquant, coordonnées hors plage, rayon ≤ 0).
""",
)
async def create_establishment(
    body: CreateEstablishmentBody, uow: UoW, _user: UserId
) -> dict[str, object]:
    uc = CreateEstablishment(uow)
    return await uc.execute(
        CreateEstablishmentCommand(
            name=body.name,
            center_lat=body.center_lat,
            center_lon=body.center_lon,
            radius_strict_m=body.radius_strict_m,
            radius_relaxed_m=body.radius_relaxed_m,
            minesec_code=body.minesec_code,
            establishment_type=body.establishment_type,
            contact_email=body.contact_email,
            contact_phone=body.contact_phone,
            territory_code=body.territory_code,
            parent_establishment_id=body.parent_establishment_id,
            designated_host_user_id=body.designated_host_user_id,
        )
    )


# ---------------------------------------------------------------------------
# GET /establishments — Lister
# ---------------------------------------------------------------------------
@router.get(
    "",
    dependencies=[Depends(RequirePermissionDep(Permission.ESTABLISHMENT_READ))],
    summary="Lister tous les établissements",
    description="""
**Rôle :** Retourne la liste complète des établissements enregistrés dans le référentiel.

**Paramètres :** Aucun filtre en V1 — tous les établissements sont retournés.

**Workflow nominal :**
1. Le client appelle la route sans paramètre.
2. Le serveur retourne la liste complète avec leurs coordonnées et `geometry_version` courant.

**Cas alternatifs :**
- Liste vide `[]` si aucun établissement n'a encore été créé.

**Cas d'exception :**
- `401` : Header `X-User-Id` absent ou invalide (en V1 dev, retourne un ID par défaut).
""",
)
async def list_establishments(
    uow: UoW,
    _user: UserId,
    pagination: PageParams = Depends(),
    territory_code: str | None = Query(
        default=None, description="Filtre exact sur le code territoire."
    ),
    name_q: str | None = Query(
        default=None,
        description="Recherche insensible à la casse sur le nom officiel (contient).",
    ),
    establishment_type: str | None = Query(
        default=None, description="Filtre exact sur le type d'établissement."
    ),
) -> Page[dict[str, object]]:
    assert uow.establishments is not None
    items, total = await uow.establishments.list_page(
        pagination.skip,
        pagination.limit,
        territory_code=territory_code,
        name_q=name_q,
        establishment_type=establishment_type,
    )
    return Page(
        items=[_establishment_dict(e) for e in items],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


# ---------------------------------------------------------------------------
# GET /establishments/summary — Synthèse (répartition par type)
# ---------------------------------------------------------------------------
@router.get(
    "/summary",
    dependencies=[Depends(RequirePermissionDep(Permission.ESTABLISHMENT_READ))],
    summary="Synthèse établissements (total et types)",
    description="""
Même périmètre que la liste sur `territory_code` et `name_q` (sans filtre `establishment_type`) :
total et nombre d'établissements par valeur de `establishment_type`.
""",
)
async def establishments_summary(
    uow: UoW,
    _user: UserId,
    territory_code: str | None = Query(default=None),
    name_q: str | None = Query(default=None),
) -> dict[str, object]:
    assert uow.establishments is not None
    by_type = await uow.establishments.count_by_establishment_type(
        territory_code=territory_code,
        name_q=name_q,
    )
    total = sum(by_type.values())
    return {"total": total, "by_establishment_type": by_type}


# ---------------------------------------------------------------------------
# GET /establishments/{id} — Détail
# ---------------------------------------------------------------------------
@router.get(
    "/{establishment_id}",
    dependencies=[Depends(RequirePermissionDep(Permission.ESTABLISHMENT_READ))],
    summary="Détail d'un établissement",
    description="""
**Rôle :** Retourne les informations complètes d'un établissement identifié par son UUID.

**Paramètre de chemin :**
- `establishment_id` : UUID de l'établissement (retourné lors de la création).

**Workflow nominal :**
1. Le serveur charge l'établissement par son identifiant.
2. Il retourne ses coordonnées, rayons et numéro de version de géométrie.

**Cas d'exception :**
- `404` : Aucun établissement ne correspond à cet identifiant (`NOT_FOUND`).
- `422` : Format UUID invalide.
""",
)
async def get_establishment(
    establishment_id: UUID = Path(..., description="UUID de l'établissement."),
    uow: UoW = ...,
    _user: UserId = ...,
) -> dict[str, object]:
    assert uow.establishments is not None
    est = await uow.establishments.get_by_id(establishment_id)
    if est is None:
        raise NotFound("Établissement introuvable.")
    return _establishment_dict(est)


# ---------------------------------------------------------------------------
# PATCH /establishments/{id} — Modifier
# ---------------------------------------------------------------------------
@router.patch(
    "/{establishment_id}",
    dependencies=[Depends(RequirePermissionDep(Permission.ESTABLISHMENT_UPDATE))],
    summary="Modifier un établissement",
    description="""
**Rôle :** Met à jour partiellement un établissement existant. Seuls les champs fournis sont modifiés (PATCH sémantique).

**Paramètre de chemin :**
- `establishment_id` : UUID de l'établissement à modifier.

**Paramètres du corps (tous optionnels) :**
- `name` : Nouveau nom officiel.
- `center_lat` / `center_lon` : Nouvelle position du centre (correction terrain).
- `radius_strict_m` / `radius_relaxed_m` : Nouveaux rayons de géofence.

**Workflow nominal :**
1. Le serveur charge l'établissement existant.
2. Il applique uniquement les champs fournis (les champs `null` ou absents sont ignorés).
3. Si au moins une valeur géographique (`center_lat`, `center_lon`, `radius_strict_m`, `radius_relaxed_m`) est modifiée, le `geometry_version` est incrémenté automatiquement — les missions déjà terminées conservent leur référence historique.
4. Les modifications sont persistées et l'établissement mis à jour est retourné.

**Cas alternatifs :**
- Aucun champ géographique modifié → `geometry_version` reste identique.
- Seul le `name` modifié → `geometry_version` inchangé.

**Cas d'exception :**
- `404` : Établissement introuvable (`NOT_FOUND`).
- `422` : Valeur hors plage (ex. lat > 90, rayon ≤ 0).
""",
)
async def update_establishment(
    establishment_id: UUID = Path(..., description="UUID de l'établissement à modifier."),
    body: UpdateEstablishmentBody = ...,
    uow: UoW = ...,
    _user: UserId = ...,
) -> dict[str, object]:
    assert uow.establishments is not None
    est = await uow.establishments.get_by_id(establishment_id)
    if est is None:
        raise NotFound("Établissement introuvable.")

    geo_changed = any(
        v is not None
        for v in (body.center_lat, body.center_lon, body.radius_strict_m, body.radius_relaxed_m)
    )

    if body.name is not None:
        est.name = body.name
    if body.center_lat is not None:
        est.center_lat = body.center_lat
    if body.center_lon is not None:
        est.center_lon = body.center_lon
    if body.radius_strict_m is not None:
        est.radius_strict_m = body.radius_strict_m
    if body.radius_relaxed_m is not None:
        est.radius_relaxed_m = body.radius_relaxed_m
    if body.minesec_code is not None:
        est.minesec_code = body.minesec_code
    if body.establishment_type is not None:
        est.establishment_type = body.establishment_type
    if body.contact_email is not None:
        est.contact_email = body.contact_email
    if body.contact_phone is not None:
        est.contact_phone = body.contact_phone
    if body.territory_code is not None:
        est.territory_code = body.territory_code
    if body.parent_establishment_id is not None:
        est.parent_establishment_id = body.parent_establishment_id
    if body.designated_host_user_id is not None:
        est.designated_host_user_id = body.designated_host_user_id
    if geo_changed:
        est.geometry_version += 1

    await uow.establishments.update(est)
    return _establishment_dict(est)


# ---------------------------------------------------------------------------
# Sérialisation
# ---------------------------------------------------------------------------
def _establishment_dict(e: object) -> dict[str, object]:
    from domain.establishment.establishment import Establishment

    assert isinstance(e, Establishment)
    return {
        "id": str(e.id),
        "name": e.name,
        "center_lat": e.center_lat,
        "center_lon": e.center_lon,
        "radius_strict_m": e.radius_strict_m,
        "radius_relaxed_m": e.radius_relaxed_m,
        "geometry_version": e.geometry_version,
        "minesec_code": e.minesec_code,
        "establishment_type": e.establishment_type,
        "contact_email": e.contact_email,
        "contact_phone": e.contact_phone,
        "territory_code": e.territory_code,
        "parent_establishment_id": str(e.parent_establishment_id)
        if e.parent_establishment_id
        else None,
        "designated_host_user_id": str(e.designated_host_user_id)
        if e.designated_host_user_id
        else None,
        "geometry_validated_at": e.geometry_validated_at.isoformat()
        if e.geometry_validated_at
        else None,
        "geometry_validated_by_user_id": str(e.geometry_validated_by_user_id)
        if e.geometry_validated_by_user_id
        else None,
    }
