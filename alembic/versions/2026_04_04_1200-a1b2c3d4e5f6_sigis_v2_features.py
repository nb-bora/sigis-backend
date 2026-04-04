"""sigis v2: territorial + rich establishments, mission workflow, outcomes, exceptions, audit

Revision ID: a1b2c3d4e5f6
Revises: 5aecd3f59a30
Create Date: 2026-04-04

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "5aecd3f59a30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # SQLite : FK / contraintes sur table existante → batch_alter_table (copie/recréation).
    with op.batch_alter_table("establishments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("minesec_code", sa.String(length=64), nullable=True))
        batch_op.add_column(
            sa.Column(
                "establishment_type", sa.String(length=64), nullable=False, server_default="other"
            ),
        )
        batch_op.add_column(
            sa.Column("contact_email", sa.String(length=320), nullable=True),
        )
        batch_op.add_column(sa.Column("contact_phone", sa.String(length=32), nullable=True))
        batch_op.add_column(
            sa.Column("territory_code", sa.String(length=64), nullable=True),
        )
        batch_op.add_column(sa.Column("parent_establishment_id", sa.Uuid(), nullable=True))
        batch_op.add_column(
            sa.Column("designated_host_user_id", sa.Uuid(), nullable=True),
        )
        batch_op.add_column(
            sa.Column("geometry_validated_at", sa.DateTime(timezone=True), nullable=True),
        )
        batch_op.add_column(
            sa.Column("geometry_validated_by_user_id", sa.Uuid(), nullable=True),
        )
        batch_op.create_foreign_key(
            "fk_establishments_parent",
            "establishments",
            ["parent_establishment_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_establishments_designated_host",
            "users",
            ["designated_host_user_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_establishments_geom_validated_by",
            "users",
            ["geometry_validated_by_user_id"],
            ["id"],
        )

    with op.batch_alter_table("missions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("designated_host_user_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("objective", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("plan_reference", sa.String(length=256), nullable=True))
        batch_op.add_column(
            sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default="0"),
        )
        batch_op.add_column(sa.Column("cancellation_reason", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        )
        batch_op.add_column(sa.Column("cancelled_by_user_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("previous_mission_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_missions_designated_host",
            "users",
            ["designated_host_user_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_missions_cancelled_by",
            "users",
            ["cancelled_by_user_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_missions_previous",
            "missions",
            ["previous_mission_id"],
            ["id"],
        )

    with op.batch_alter_table("exception_requests", schema=None) as batch_op:
        batch_op.add_column(sa.Column("assigned_to_user_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("internal_comment", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True),
        )
        batch_op.add_column(
            sa.Column("attachment_url", sa.String(length=1024), nullable=True),
        )
        batch_op.create_foreign_key(
            "fk_exception_assigned_to",
            "users",
            ["assigned_to_user_id"],
            ["id"],
        )

    op.create_table(
        "mission_outcomes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("mission_id", sa.Uuid(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("compliance_level", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["mission_id"], ["missions.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mission_id", name="uq_mission_outcomes_mission_id"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("mission_outcomes")

    with op.batch_alter_table("exception_requests", schema=None) as batch_op:
        batch_op.drop_constraint("fk_exception_assigned_to", type_="foreignkey")
        batch_op.drop_column("attachment_url")
        batch_op.drop_column("sla_due_at")
        batch_op.drop_column("internal_comment")
        batch_op.drop_column("assigned_to_user_id")

    with op.batch_alter_table("missions", schema=None) as batch_op:
        batch_op.drop_constraint("fk_missions_previous", type_="foreignkey")
        batch_op.drop_constraint("fk_missions_cancelled_by", type_="foreignkey")
        batch_op.drop_constraint("fk_missions_designated_host", type_="foreignkey")
        batch_op.drop_column("previous_mission_id")
        batch_op.drop_column("cancelled_by_user_id")
        batch_op.drop_column("cancelled_at")
        batch_op.drop_column("cancellation_reason")
        batch_op.drop_column("requires_approval")
        batch_op.drop_column("plan_reference")
        batch_op.drop_column("objective")
        batch_op.drop_column("designated_host_user_id")

    with op.batch_alter_table("establishments", schema=None) as batch_op:
        batch_op.drop_constraint("fk_establishments_geom_validated_by", type_="foreignkey")
        batch_op.drop_constraint("fk_establishments_designated_host", type_="foreignkey")
        batch_op.drop_constraint("fk_establishments_parent", type_="foreignkey")
        batch_op.drop_column("geometry_validated_by_user_id")
        batch_op.drop_column("geometry_validated_at")
        batch_op.drop_column("designated_host_user_id")
        batch_op.drop_column("parent_establishment_id")
        batch_op.drop_column("territory_code")
        batch_op.drop_column("contact_phone")
        batch_op.drop_column("contact_email")
        batch_op.drop_column("establishment_type")
        batch_op.drop_column("minesec_code")
