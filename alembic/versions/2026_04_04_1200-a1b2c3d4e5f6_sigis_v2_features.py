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
    op.add_column("establishments", sa.Column("minesec_code", sa.String(length=64), nullable=True))
    op.add_column(
        "establishments",
        sa.Column("establishment_type", sa.String(length=64), nullable=False, server_default="other"),
    )
    op.add_column("establishments", sa.Column("contact_email", sa.String(length=320), nullable=True))
    op.add_column("establishments", sa.Column("contact_phone", sa.String(length=32), nullable=True))
    op.add_column("establishments", sa.Column("territory_code", sa.String(length=64), nullable=True))
    op.add_column("establishments", sa.Column("parent_establishment_id", sa.Uuid(), nullable=True))
    op.add_column(
        "establishments",
        sa.Column("designated_host_user_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "establishments",
        sa.Column("geometry_validated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "establishments",
        sa.Column("geometry_validated_by_user_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_establishments_parent",
        "establishments",
        "establishments",
        ["parent_establishment_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_establishments_designated_host",
        "establishments",
        "users",
        ["designated_host_user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_establishments_geom_validated_by",
        "establishments",
        "users",
        ["geometry_validated_by_user_id"],
        ["id"],
    )

    op.add_column(
        "missions",
        sa.Column("designated_host_user_id", sa.Uuid(), nullable=True),
    )
    op.add_column("missions", sa.Column("objective", sa.Text(), nullable=True))
    op.add_column("missions", sa.Column("plan_reference", sa.String(length=256), nullable=True))
    op.add_column(
        "missions",
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column("missions", sa.Column("cancellation_reason", sa.Text(), nullable=True))
    op.add_column("missions", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("missions", sa.Column("cancelled_by_user_id", sa.Uuid(), nullable=True))
    op.add_column("missions", sa.Column("previous_mission_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_missions_designated_host",
        "missions",
        "users",
        ["designated_host_user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_missions_cancelled_by",
        "missions",
        "users",
        ["cancelled_by_user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_missions_previous",
        "missions",
        "missions",
        ["previous_mission_id"],
        ["id"],
    )

    op.add_column("exception_requests", sa.Column("assigned_to_user_id", sa.Uuid(), nullable=True))
    op.add_column("exception_requests", sa.Column("internal_comment", sa.Text(), nullable=True))
    op.add_column(
        "exception_requests",
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("exception_requests", sa.Column("attachment_url", sa.String(length=1024), nullable=True))
    op.create_foreign_key(
        "fk_exception_assigned_to",
        "exception_requests",
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

    op.drop_constraint("fk_exception_assigned_to", "exception_requests", type_="foreignkey")
    op.drop_column("exception_requests", "attachment_url")
    op.drop_column("exception_requests", "sla_due_at")
    op.drop_column("exception_requests", "internal_comment")
    op.drop_column("exception_requests", "assigned_to_user_id")

    op.drop_constraint("fk_missions_previous", "missions", type_="foreignkey")
    op.drop_constraint("fk_missions_cancelled_by", "missions", type_="foreignkey")
    op.drop_constraint("fk_missions_designated_host", "missions", type_="foreignkey")
    op.drop_column("missions", "previous_mission_id")
    op.drop_column("missions", "cancelled_by_user_id")
    op.drop_column("missions", "cancelled_at")
    op.drop_column("missions", "cancellation_reason")
    op.drop_column("missions", "requires_approval")
    op.drop_column("missions", "plan_reference")
    op.drop_column("missions", "objective")
    op.drop_column("missions", "designated_host_user_id")

    op.drop_constraint("fk_establishments_geom_validated_by", "establishments", type_="foreignkey")
    op.drop_constraint("fk_establishments_designated_host", "establishments", type_="foreignkey")
    op.drop_constraint("fk_establishments_parent", "establishments", type_="foreignkey")
    op.drop_column("establishments", "geometry_validated_by_user_id")
    op.drop_column("establishments", "geometry_validated_at")
    op.drop_column("establishments", "designated_host_user_id")
    op.drop_column("establishments", "parent_establishment_id")
    op.drop_column("establishments", "territory_code")
    op.drop_column("establishments", "contact_phone")
    op.drop_column("establishments", "contact_email")
    op.drop_column("establishments", "establishment_type")
    op.drop_column("establishments", "minesec_code")
