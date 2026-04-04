"""Un seul rôle par utilisateur (colonne users.role, suppression de user_roles).

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-05

"""

from collections import defaultdict
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# En cas de doublons historiques : conserver le rôle le plus élevé dans la hiérarchie métier.
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


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(length=64), nullable=True))

    conn = op.get_bind()
    rows = conn.execute(text("SELECT user_id, role FROM user_roles")).fetchall()
    by_user: dict[str, list[str]] = defaultdict(list)
    for user_id, role in rows:
        by_user[str(user_id)].append(role)

    for uid, rlist in by_user.items():
        conn.execute(
            text("UPDATE users SET role = :role WHERE id = :id"),
            {"role": _pick_role(rlist), "id": uid},
        )

    conn.execute(
        text("UPDATE users SET role = 'INSPECTOR' WHERE role IS NULL"),
    )

    # SQLite : ALTER COLUMN … NOT NULL n'est pas supporté sans recréation de table
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column("role", existing_type=sa.String(length=64), nullable=False)

    op.drop_table("user_roles")


def downgrade() -> None:
    op.create_table(
        "user_roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role", name="uq_user_role"),
    )

    conn = op.get_bind()
    users = conn.execute(text("SELECT id, role FROM users")).fetchall()
    import uuid

    for uid, role in users:
        conn.execute(
            text("INSERT INTO user_roles (id, user_id, role) VALUES (:id, :uid, :role)"),
            {"id": str(uuid.uuid4()), "uid": str(uid), "role": role},
        )

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("role")
