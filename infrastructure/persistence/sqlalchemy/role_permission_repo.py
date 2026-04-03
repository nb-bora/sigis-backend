"""Dépôt de persistance pour les permissions des rôles."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.identity.permission import Permission
from domain.identity.role import Role
from infrastructure.persistence.sqlalchemy.models import RolePermissionModel


class RolePermissionRepositoryImpl:
    """
    Gère les permissions effectives par rôle en base de données.

    La méthode ``seed_defaults`` est appelée au démarrage de l'application
    pour initialiser les permissions manquantes sans écraser les surcharges
    existantes.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Lecture ───────────────────────────────────────────────────────────

    async def get_permissions_for_role(self, role: Role) -> set[Permission]:
        stmt = select(RolePermissionModel).where(RolePermissionModel.role == role.value)
        rows = (await self._session.execute(stmt)).scalars().all()
        result: set[Permission] = set()
        for row in rows:
            try:
                result.add(Permission(row.permission))
            except ValueError:
                pass  # permission obsolète ignorée
        return result

    async def get_all_roles_permissions(self) -> dict[str, list[str]]:
        """Retourne le dictionnaire complet {role: [permissions]} depuis la base."""
        stmt = select(RolePermissionModel).order_by(
            RolePermissionModel.role, RolePermissionModel.permission
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        result: dict[str, list[str]] = {}
        for row in rows:
            result.setdefault(row.role, []).append(row.permission)
        return result

    async def get_effective_permissions(self, roles: list[Role]) -> set[Permission]:
        """Retourne l'union des permissions de tous les rôles donnés."""
        result: set[Permission] = set()
        for role in roles:
            result |= await self.get_permissions_for_role(role)
        return result

    # ── Écriture ──────────────────────────────────────────────────────────

    async def add_permission(self, role: Role, permission: Permission) -> bool:
        """
        Ajoute une permission à un rôle.

        Retourne ``True`` si ajoutée, ``False`` si déjà présente (idempotent).
        """
        existing = await self._get_row(role, permission)
        if existing is not None:
            return False
        self._session.add(
            RolePermissionModel(id=uuid.uuid4(), role=role.value, permission=permission.value)
        )
        return True

    async def remove_permission(self, role: Role, permission: Permission) -> bool:
        """
        Retire une permission d'un rôle.

        Retourne ``True`` si retirée, ``False`` si absente.
        """
        existing = await self._get_row(role, permission)
        if existing is None:
            return False
        await self._session.delete(existing)
        return True

    async def set_permissions(self, role: Role, permissions: set[Permission]) -> None:
        """
        Remplace entièrement les permissions d'un rôle (sans doublons).

        Supprime celles qui ne sont plus dans la liste, ajoute les nouvelles.
        """
        current = await self._get_all_rows(role)
        current_set = {
            Permission(r.permission)
            for r in current
            if r.permission in Permission._value2member_map_
        }
        to_add = permissions - current_set
        to_remove = current_set - permissions

        for row in current:
            try:
                if Permission(row.permission) in to_remove:
                    await self._session.delete(row)
            except ValueError:
                await self._session.delete(row)

        for perm in to_add:
            self._session.add(
                RolePermissionModel(id=uuid.uuid4(), role=role.value, permission=perm.value)
            )

    async def seed_defaults(self, defaults: dict[str, list[str]]) -> int:
        """
        Insère les permissions par défaut manquantes (sans écraser l'existant).

        Retourne le nombre d'entrées insérées.
        """
        inserted = 0
        for role_value, perms in defaults.items():
            for perm_value in perms:
                stmt = select(RolePermissionModel).where(
                    RolePermissionModel.role == role_value,
                    RolePermissionModel.permission == perm_value,
                )
                exists = (await self._session.execute(stmt)).scalars().first()
                if exists is None:
                    self._session.add(
                        RolePermissionModel(
                            id=uuid.uuid4(),
                            role=role_value,
                            permission=perm_value,
                        )
                    )
                    inserted += 1
        return inserted

    # ── privé ─────────────────────────────────────────────────────────────

    async def _get_row(self, role: Role, permission: Permission) -> RolePermissionModel | None:
        stmt = select(RolePermissionModel).where(
            RolePermissionModel.role == role.value,
            RolePermissionModel.permission == permission.value,
        )
        return (await self._session.execute(stmt)).scalars().first()

    async def _get_all_rows(self, role: Role) -> list[RolePermissionModel]:
        stmt = select(RolePermissionModel).where(RolePermissionModel.role == role.value)
        return list((await self._session.execute(stmt)).scalars().all())
