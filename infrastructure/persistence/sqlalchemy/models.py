"""Modèles ORM — tables V1 pilote."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from infrastructure.persistence.sqlalchemy.base import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    # Numéro en format E.164 : +237XXXXXXXXX (conforme PNN ART 2014)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    roles: Mapped[list["UserRoleModel"]] = relationship(
        "UserRoleModel", back_populates="user", cascade="all, delete-orphan"
    )
    reset_tokens: Mapped[list["PasswordResetTokenModel"]] = relationship(
        "PasswordResetTokenModel", back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("phone_number", name="uq_users_phone_number"),
    )


class UserRoleModel(Base):
    """Association utilisateur ↔ rôle."""

    __tablename__ = "user_roles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(64), nullable=False)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="roles")

    __table_args__ = (UniqueConstraint("user_id", "role", name="uq_user_role"),)


class PasswordResetTokenModel(Base):
    """Jeton de réinitialisation de mot de passe (usage unique, expirant)."""

    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    # hash SHA-256 du token brut envoyé par e-mail
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="reset_tokens")


class RolePermissionModel(Base):
    """
    Permissions effectives d'un rôle.

    La table est initialisée avec les valeurs par défaut de
    ``domain.identity.role_defaults.ROLE_DEFAULT_PERMISSIONS``.
    Les surcharges (ajouts / retraits) sont appliquées via l'API
    ``PATCH /v1/roles/{role}/permissions``.
    Contrainte d'unicité (role, permission) : aucun doublon possible.
    """

    __tablename__ = "role_permissions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    permission: Mapped[str] = mapped_column(String(128), nullable=False)

    __table_args__ = (UniqueConstraint("role", "permission", name="uq_role_permission"),)


class EstablishmentModel(Base):
    __tablename__ = "establishments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(512))
    center_lat: Mapped[float] = mapped_column()
    center_lon: Mapped[float] = mapped_column()
    radius_strict_m: Mapped[float] = mapped_column()
    radius_relaxed_m: Mapped[float] = mapped_column()
    geometry_version: Mapped[int] = mapped_column(default=1)
    minesec_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    establishment_type: Mapped[str] = mapped_column(String(64), default="other")
    contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    territory_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parent_establishment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("establishments.id"), nullable=True
    )
    designated_host_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    geometry_validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    geometry_validated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )


class MissionModel(Base):
    __tablename__ = "missions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    establishment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("establishments.id")
    )
    inspector_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="planned")
    host_token: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True))
    sms_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    designated_host_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_reference: Mapped[str | None] = mapped_column(String(256), nullable=True)
    requires_approval: Mapped[bool] = mapped_column(default=False)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    previous_mission_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("missions.id"), nullable=True
    )

    site_visit: Mapped["SiteVisitModel | None"] = relationship(
        "SiteVisitModel",
        back_populates="mission",
        uselist=False,
    )


class SiteVisitModel(Base):
    __tablename__ = "site_visits"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mission_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("missions.id"), unique=True
    )
    status: Mapped[str] = mapped_column(String(64))
    host_validation_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checked_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    inspector_lat: Mapped[float | None] = mapped_column(nullable=True)
    inspector_lon: Mapped[float | None] = mapped_column(nullable=True)
    host_lat: Mapped[float | None] = mapped_column(nullable=True)
    host_lon: Mapped[float | None] = mapped_column(nullable=True)

    mission: Mapped["MissionModel"] = relationship("MissionModel", back_populates="site_visit")


class PresenceProofModel(Base):
    __tablename__ = "presence_proofs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_visit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("site_visits.id")
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    latitude: Mapped[float] = mapped_column()
    longitude: Mapped[float] = mapped_column()
    geofence_status: Mapped[str] = mapped_column(String(32))


class CoPresenceEventModel(Base):
    __tablename__ = "copresence_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_visit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("site_visits.id")
    )
    validated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    host_validation_mode: Mapped[str] = mapped_column(String(32))


class ExceptionRequestModel(Base):
    __tablename__ = "exception_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mission_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("missions.id"))
    author_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(Text)
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    internal_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attachment_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)


class MissionOutcomeModel(Base):
    __tablename__ = "mission_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mission_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("missions.id"), unique=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    compliance_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class IdempotencyRecordModel(Base):
    __tablename__ = "idempotency_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope: Mapped[str] = mapped_column(String(64))
    client_key: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    response_body: Mapped[str] = mapped_column(Text)

    __table_args__ = (UniqueConstraint("scope", "client_key", name="uq_idempotency_scope_key"),)
