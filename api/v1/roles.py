"""
Routeur de gestion des rôles et de leurs permissions SIGIS.

Routes exposées :
  GET    /roles                                — Liste tous les rôles avec leurs permissions
  GET    /roles/{role}/permissions             — Permissions effectives d'un rôle
  PUT    /roles/{role}/permissions             — Remplace entièrement les permissions d'un rôle
  POST   /roles/{role}/permissions/{perm}      — Ajoute une permission à un rôle
  DELETE /roles/{role}/permissions/{perm}      — Retire une permission d'un rôle
  POST   /roles/{role}/permissions/reset       — Réinitialise aux permissions par défaut
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import RequireRolesDep, UoW
from domain.identity.permission import Permission
from domain.identity.role import Role
from domain.identity.role_defaults import default_permissions_for

router = APIRouter(prefix="/roles", tags=["Rôles & Permissions"])

_super_admins = [Role.SUPER_ADMIN]
_admins = [Role.SUPER_ADMIN, Role.NATIONAL_ADMIN]


# ── GET /roles ─────────────────────────────────────────────────────────────


@router.get(
    "",
    summary="Lister tous les rôles et leurs permissions",
    description="""
**Rôle** : Retourne pour chaque rôle du système la liste des permissions qui lui sont
actuellement attribuées (prenant en compte toutes les surcharges administrateur).

**Accès** : `SUPER_ADMIN` ou `NATIONAL_ADMIN`.

**Workflow** :
1. Récupère toutes les lignes de la table `role_permissions`
2. Regroupe par rôle
3. Complète avec les rôles sans permissions (liste vide)

**Lecture du résultat** :
```json
{
  "SUPER_ADMIN":  ["ESTABLISHMENT_CREATE", "ESTABLISHMENT_READ", ...],
  "INSPECTOR":    ["VISIT_CHECKIN", "VISIT_CHECKOUT", ...]
}
```
""",
)
async def list_roles(
    uow: UoW,
    _: None = Depends(RequireRolesDep(_admins)),
) -> dict[str, list[str]]:
    data = await uow.role_permissions.get_all_roles_permissions()
    # Garantir la présence de tous les rôles même sans permissions
    for role in Role:
        data.setdefault(role.value, [])
    return data


# ── GET /roles/{role}/permissions ──────────────────────────────────────────


@router.get(
    "/{role}/permissions",
    summary="Permissions effectives d'un rôle",
    description="""
**Rôle** : Retourne la liste des permissions actuellement attribuées à un rôle précis.

**Paramètres** :
- `role` — nom du rôle (`SUPER_ADMIN`, `NATIONAL_ADMIN`, `REGIONAL_SUPERVISOR`, `INSPECTOR`, `HOST`)

**Accès** : `SUPER_ADMIN` ou `NATIONAL_ADMIN`.

**Exceptions** :
- `404` — rôle inconnu
""",
)
async def get_role_permissions(
    role: str,
    uow: UoW,
    _: None = Depends(RequireRolesDep(_admins)),
) -> dict[str, list[str]]:
    role_enum = _parse_role(role)
    perms = await uow.role_permissions.get_permissions_for_role(role_enum)
    return {"role": role_enum.value, "permissions": sorted(p.value for p in perms)}


# ── PUT /roles/{role}/permissions ──────────────────────────────────────────


@router.put(
    "/{role}/permissions",
    summary="Remplacer entièrement les permissions d'un rôle",
    description="""
**Rôle** : Remplace la liste complète des permissions d'un rôle par celle fournie
dans le corps de la requête (sans doublons).

**Accès** : `SUPER_ADMIN` uniquement.

**Paramètres** :
- `role` — nom du rôle ciblé
- Corps (JSON) : `{"permissions": ["PERMISSION_A", "PERMISSION_B", ...]}`

**Workflow** :
1. Validation de chaque permission (404 si inconnue)
2. Suppression des permissions retirées
3. Ajout des nouvelles permissions
4. Retour de la liste mise à jour

**Exceptions** :
- `404` — rôle ou permission inconnue
""",
)
async def set_role_permissions(
    role: str,
    body: dict,
    uow: UoW,
    _: None = Depends(RequireRolesDep(_super_admins)),
) -> dict[str, list[str]]:
    role_enum = _parse_role(role)
    raw_perms: list[str] = body.get("permissions", [])
    perm_set = {_parse_permission(p) for p in raw_perms}
    await uow.role_permissions.set_permissions(role_enum, perm_set)
    return {"role": role_enum.value, "permissions": sorted(p.value for p in perm_set)}


# ── POST /roles/{role}/permissions/{perm} ─────────────────────────────────


@router.post(
    "/{role}/permissions/{perm}",
    status_code=status.HTTP_200_OK,
    summary="Ajouter une permission à un rôle",
    description="""
**Rôle** : Attribue une permission supplémentaire à un rôle existant.
L'opération est idempotente : si la permission est déjà présente, rien ne change.

**Accès** : `SUPER_ADMIN` uniquement.

**Paramètres** :
- `role` — nom du rôle ciblé
- `perm` — identifiant de la permission à ajouter

**Exceptions** :
- `404` — rôle ou permission inconnue
""",
)
async def add_permission(
    role: str,
    perm: str,
    uow: UoW,
    _: None = Depends(RequireRolesDep(_super_admins)),
) -> dict:
    role_enum = _parse_role(role)
    perm_enum = _parse_permission(perm)
    added = await uow.role_permissions.add_permission(role_enum, perm_enum)
    return {
        "role": role_enum.value,
        "permission": perm_enum.value,
        "added": added,
        "detail": "Permission ajoutée."
        if added
        else "Permission déjà présente (aucune modification).",
    }


# ── DELETE /roles/{role}/permissions/{perm} ────────────────────────────────


@router.delete(
    "/{role}/permissions/{perm}",
    status_code=status.HTTP_200_OK,
    summary="Retirer une permission d'un rôle",
    description="""
**Rôle** : Supprime une permission d'un rôle.
L'opération est idempotente : si la permission est absente, rien ne change.

**Accès** : `SUPER_ADMIN` uniquement.

**Paramètres** :
- `role` — nom du rôle ciblé
- `perm` — identifiant de la permission à retirer

**Attention** : Retirer une permission d'un rôle affecte immédiatement tous les
utilisateurs portant ce rôle.

**Exceptions** :
- `404` — rôle ou permission inconnue
""",
)
async def remove_permission(
    role: str,
    perm: str,
    uow: UoW,
    _: None = Depends(RequireRolesDep(_super_admins)),
) -> dict:
    role_enum = _parse_role(role)
    perm_enum = _parse_permission(perm)
    removed = await uow.role_permissions.remove_permission(role_enum, perm_enum)
    return {
        "role": role_enum.value,
        "permission": perm_enum.value,
        "removed": removed,
        "detail": "Permission retirée." if removed else "Permission absente (aucune modification).",
    }


# ── POST /roles/{role}/permissions/reset ──────────────────────────────────


@router.post(
    "/{role}/permissions/reset",
    status_code=status.HTTP_200_OK,
    summary="Réinitialiser les permissions d'un rôle aux valeurs par défaut",
    description="""
**Rôle** : Restaure les permissions d'un rôle à leur valeur initiale définie
dans le code source (`domain/identity/role_defaults.py`).

**Accès** : `SUPER_ADMIN` uniquement.

**Workflow** :
1. Supprime toutes les permissions actuelles du rôle
2. Réinsère les permissions par défaut

**Exceptions** :
- `404` — rôle inconnu
""",
)
async def reset_permissions(
    role: str,
    uow: UoW,
    _: None = Depends(RequireRolesDep(_super_admins)),
) -> dict[str, list[str]]:
    role_enum = _parse_role(role)
    defaults = default_permissions_for(role_enum)
    await uow.role_permissions.set_permissions(role_enum, defaults)
    return {
        "role": role_enum.value,
        "permissions": sorted(p.value for p in defaults),
        "detail": "Permissions réinitialisées aux valeurs par défaut.",
    }


# ── GET /roles/permissions/catalog ────────────────────────────────────────


@router.get(
    "/permissions/catalog",
    summary="Catalogue de toutes les permissions disponibles",
    description="""
**Rôle** : Retourne la liste exhaustive de toutes les permissions que peut utiliser
le système SIGIS, avec leur description.

**Accès** : `SUPER_ADMIN` ou `NATIONAL_ADMIN`.
""",
)
async def list_permissions(
    _: None = Depends(RequireRolesDep(_admins)),
) -> dict[str, list[str]]:
    catalog: dict[str, list[str]] = {}
    for perm in Permission:
        prefix = perm.value.split("_")[0]
        catalog.setdefault(prefix, []).append(perm.value)
    return catalog


# ── helpers ────────────────────────────────────────────────────────────────


def _parse_role(role_str: str) -> Role:
    try:
        return Role(role_str.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rôle « {role_str} » inconnu. Valeurs acceptées : {[r.value for r in Role]}",
        )


def _parse_permission(perm_str: str) -> Permission:
    try:
        return Permission(perm_str.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Permission « {perm_str} » inconnue. Consultez GET /roles/permissions/catalog",
        )
