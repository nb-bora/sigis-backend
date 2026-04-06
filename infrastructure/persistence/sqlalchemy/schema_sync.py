"""
Alignement schéma ``users`` sur le modèle actuel (colonne ``role``).

En développement, ``create_all`` ne modifie pas les tables existantes.
SQLite : détection des colonnes via ``PRAGMA table_info`` (plus fiable que
``inspect`` selon les versions). Les étapes après ``ALTER TABLE`` sont isolées
pour qu'un échec (ex. ``DROP user_roles``) n'annule pas l'ajout de ``role``.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from uuid import UUID

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

_LOG = logging.getLogger(__name__)

_ROLE_PRIORITY = (
    "SUPER_ADMIN",
    "NATIONAL_ADMIN",
    "REGIONAL_SUPERVISOR",
    "INSPECTOR",
    "HOST",
)


def _pick_role(values: list[str]) -> str:
    if not values:
        return "INSPECTOR"
    return min(values, key=lambda r: _ROLE_PRIORITY.index(r) if r in _ROLE_PRIORITY else 99)


def _column_names(connection: Connection, table: str) -> set[str]:
    dialect = connection.dialect.name
    if dialect == "sqlite":
        rows = connection.execute(text(f"PRAGMA table_info({table})")).fetchall()
        return {r[1] for r in rows}
    insp = inspect(connection)
    if table not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def ensure_users_role_column(connection: Connection) -> None:
    """
    Ajoute ``users.role`` si absent (transaction courante).

    Ne dépend pas de ``inspect().get_columns`` pour SQLite (PRAGMA).
    """
    tables = inspect(connection).get_table_names()
    if "users" not in tables:
        return

    col_names = _column_names(connection, "users")
    if "role" in col_names:
        return

    dialect = connection.dialect.name
    if dialect == "sqlite":
        connection.execute(
            text("ALTER TABLE users ADD COLUMN role VARCHAR(64) NOT NULL DEFAULT 'INSPECTOR'")
        )
    else:
        connection.execute(
            text("ALTER TABLE users ADD COLUMN role VARCHAR(64) DEFAULT 'INSPECTOR'")
        )
    _LOG.info("Schéma : colonne users.role ajoutée.")


def migrate_user_roles_table(connection: Connection) -> None:
    """
    Recopie ``user_roles`` vers ``users.role`` puis supprime ``user_roles``.

    À appeler après ``ensure_users_role_column`` ; les erreurs sont journalisées
    sans faire échouer la migration de colonne.
    """
    tables = inspect(connection).get_table_names()
    if "user_roles" not in tables or "users" not in tables:
        return
    if "role" not in _column_names(connection, "users"):
        return

    dialect = connection.dialect.name
    try:
        rows = connection.execute(text("SELECT user_id, role FROM user_roles")).fetchall()
        by_user: dict[str, list[str]] = defaultdict(list)
        for user_id, role in rows:
            by_user[str(user_id)].append(role)

        for uid_str, rlist in by_user.items():
            role = _pick_role(rlist)
            try:
                uid = UUID(uid_str) if isinstance(uid_str, str) else uid_str
            except ValueError:
                continue
            connection.execute(
                text("UPDATE users SET role = :role WHERE id = :id"),
                {"role": role, "id": uid},
            )

        if dialect == "postgresql":
            connection.execute(text("ALTER TABLE users ALTER COLUMN role SET NOT NULL"))

        connection.execute(text("DROP TABLE user_roles"))
        _LOG.info("Schéma : table user_roles migrée puis supprimée.")
    except Exception as exc:
        _LOG.warning(
            "Schéma : migration user_roles ignorée (%s). La colonne users.role existe.",
            exc,
        )

    try:
        connection.execute(
            text("UPDATE users SET role = 'INSPECTOR' WHERE role IS NULL OR role = ''")
        )
    except Exception as exc:
        _LOG.warning("Schéma : nettoyage users.role ignoré (%s).", exc)
