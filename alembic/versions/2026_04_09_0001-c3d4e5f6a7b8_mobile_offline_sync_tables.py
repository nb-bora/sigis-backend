"""mobile offline: devices, events, qr jti, audit hash chain

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-09

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | Sequence[str] | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mobile_devices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("public_key_ed25519", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "public_key_ed25519", name="uq_mobile_device_user_pk"),
    )

    op.create_table(
        "mobile_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("mission_id", sa.Uuid(), nullable=False),
        sa.Column("site_visit_id", sa.Uuid(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("client_request_id", sa.String(length=128), nullable=False),
        sa.Column("captured_at_client", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at_server", sa.DateTime(timezone=True), nullable=False),
        sa.Column("gps_lat", sa.Float(), nullable=True),
        sa.Column("gps_lon", sa.Float(), nullable=True),
        sa.Column("gps_accuracy_m", sa.Float(), nullable=True),
        sa.Column("gps_provider", sa.String(length=32), nullable=True),
        sa.Column("selfie_sha256", sa.String(length=64), nullable=True),
        sa.Column("selfie_mime", sa.String(length=64), nullable=True),
        sa.Column("selfie_w", sa.Integer(), nullable=True),
        sa.Column("selfie_h", sa.Integer(), nullable=True),
        sa.Column("prev_event_hash", sa.String(length=64), nullable=True),
        sa.Column("event_hash", sa.String(length=64), nullable=False),
        sa.Column("signature_ed25519", sa.String(length=256), nullable=False),
        sa.Column("raw_json", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["device_id"], ["mobile_devices.id"]),
        sa.ForeignKeyConstraint(["mission_id"], ["missions.id"]),
        sa.ForeignKeyConstraint(["site_visit_id"], ["site_visits.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "device_id", "client_request_id", name="uq_mobile_event_device_client_req"
        ),
        sa.UniqueConstraint("device_id", "event_hash", name="uq_mobile_event_device_hash"),
    )

    op.create_table(
        "used_qr_jti",
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("mission_id", sa.Uuid(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["mission_id"], ["missions.id"]),
        sa.PrimaryKeyConstraint("jti"),
    )

    op.create_table(
        "audit_chain_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("prev_hash", sa.String(length=64), nullable=True),
        sa.Column("entry_hash", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("audit_chain_entries")
    op.drop_table("used_qr_jti")
    op.drop_table("mobile_events")
    op.drop_table("mobile_devices")
