"""Modèles ORM — tables V1 pilote."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from infrastructure.persistence.sqlalchemy.base import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)


class EstablishmentModel(Base):
    __tablename__ = "establishments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(512))
    center_lat: Mapped[float] = mapped_column()
    center_lon: Mapped[float] = mapped_column()
    radius_strict_m: Mapped[float] = mapped_column()
    radius_relaxed_m: Mapped[float] = mapped_column()
    geometry_version: Mapped[int] = mapped_column(default=1)


class MissionModel(Base):
    __tablename__ = "missions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    establishment_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("establishments.id"))
    inspector_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="planned")
    host_token: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True))
    sms_code: Mapped[str | None] = mapped_column(String(32), nullable=True)

    site_visit: Mapped["SiteVisitModel | None"] = relationship(
        "SiteVisitModel",
        back_populates="mission",
        uselist=False,
    )


class SiteVisitModel(Base):
    __tablename__ = "site_visits"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mission_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("missions.id"), unique=True)
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
    site_visit_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("site_visits.id"))
    actor_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    latitude: Mapped[float] = mapped_column()
    longitude: Mapped[float] = mapped_column()
    geofence_status: Mapped[str] = mapped_column(String(32))


class CoPresenceEventModel(Base):
    __tablename__ = "copresence_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_visit_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("site_visits.id"))
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


class IdempotencyRecordModel(Base):
    __tablename__ = "idempotency_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope: Mapped[str] = mapped_column(String(64))
    client_key: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    response_body: Mapped[str] = mapped_column(Text)

    __table_args__ = (UniqueConstraint("scope", "client_key", name="uq_idempotency_scope_key"),)
