"""Interfaces de persistance — implémentées dans l'infrastructure."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from domain.audit.audit_log_entry import AuditLogEntry
from domain.establishment.establishment import Establishment
from domain.exception_request.exception_request import ExceptionRequest, ExceptionRequestStatus
from domain.identity.role import Role
from domain.identity.user import User
from domain.mission.mission import Mission
from domain.mission.mission_outcome import MissionOutcome
from domain.presence.models import CoPresenceEvent, PresenceProof
from domain.site_visit.site_visit import SiteVisit


class EstablishmentRepository(Protocol):
    async def get_by_id(self, eid: UUID) -> Establishment | None: ...

    async def add(self, est: Establishment) -> None: ...

    async def update(self, est: Establishment) -> None: ...

    async def list_all(self) -> list[Establishment]: ...

    async def list_page(
        self,
        offset: int,
        limit: int,
        *,
        territory_code: str | None = None,
        name_q: str | None = None,
        establishment_type: str | None = None,
    ) -> tuple[list[Establishment], int]: ...

    async def count_by_establishment_type(
        self,
        *,
        territory_code: str | None = None,
        name_q: str | None = None,
    ) -> dict[str, int]: ...


class MissionRepository(Protocol):
    async def get_by_id(self, mission_id: UUID) -> Mission | None: ...

    async def save(self, mission: Mission) -> None: ...

    async def update(self, mission: Mission) -> None: ...

    async def list_all(
        self,
        inspector_id: UUID | None = None,
        establishment_id: UUID | None = None,
        status: str | None = None,
        territory_code: str | None = None,
        window_from: datetime | None = None,
        window_to: datetime | None = None,
    ) -> list[Mission]: ...

    async def list_page(
        self,
        offset: int,
        limit: int,
        *,
        inspector_id: UUID | None = None,
        establishment_id: UUID | None = None,
        status: str | None = None,
        territory_code: str | None = None,
        window_from: datetime | None = None,
        window_to: datetime | None = None,
    ) -> tuple[list[Mission], int]: ...

    async def count_by_status(
        self,
        *,
        inspector_id: UUID | None = None,
        establishment_id: UUID | None = None,
        territory_code: str | None = None,
        window_from: datetime | None = None,
        window_to: datetime | None = None,
    ) -> dict[str, int]: ...


class SiteVisitRepository(Protocol):
    async def get_by_id(self, site_visit_id: UUID) -> SiteVisit | None: ...

    async def get_by_mission_id(self, mission_id: UUID) -> SiteVisit | None: ...

    async def save(self, site_visit: SiteVisit) -> None: ...


class PresenceProofRepository(Protocol):
    async def add(self, proof: PresenceProof) -> None: ...


class CoPresenceEventRepository(Protocol):
    async def add(self, event: CoPresenceEvent, *, host_validation_mode: str) -> None: ...


class ExceptionRequestRepository(Protocol):
    async def get_by_id(self, rid: UUID) -> ExceptionRequest | None: ...

    async def add(self, req: ExceptionRequest) -> None: ...

    async def update(self, req: ExceptionRequest) -> None: ...

    async def list_by_mission_id(self, mission_id: UUID) -> list[ExceptionRequest]: ...

    async def list_all(self, status: str | None = None) -> list[ExceptionRequest]: ...

    async def list_page(
        self,
        offset: int,
        limit: int,
        *,
        status: str | None = None,
        mission_id: UUID | None = None,
        author_user_id: UUID | None = None,
        assigned_to_user_id: UUID | None = None,
        unassigned_only: bool = False,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        message_q: str | None = None,
    ) -> tuple[list[ExceptionRequest], int]: ...

    async def count_by_status(
        self,
        *,
        mission_id: UUID | None = None,
        author_user_id: UUID | None = None,
        assigned_to_user_id: UUID | None = None,
        unassigned_only: bool = False,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        message_q: str | None = None,
    ) -> dict[str, int]: ...

    async def update_status(
        self, exception_id: UUID, new_status: ExceptionRequestStatus
    ) -> None: ...


class UserRepository(Protocol):
    async def get_by_id(self, user_id: UUID) -> User: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def get_by_phone(self, phone: str) -> User | None: ...

    async def list_all(self) -> list[User]: ...

    async def list_page(
        self,
        offset: int,
        limit: int,
        *,
        q: str | None = None,
        role: Role | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[User], int]: ...

    async def create(self, user: User) -> None: ...

    async def update(self, user: User) -> None: ...


class IdempotencyRepository(Protocol):
    async def get_response(self, scope: str, client_key: str) -> str | None: ...

    async def save(self, scope: str, client_key: str, response_body: str) -> None: ...


class PasswordResetTokenRecord(Protocol):
    """Vue minimale du jeton pour le cas d'usage reset_password."""

    user_id: UUID


class PasswordResetTokenRepository(Protocol):
    async def create(self, user_id: UUID, raw_token: str, expires_at: datetime) -> None: ...

    async def get_valid(self, raw_token: str) -> PasswordResetTokenRecord | None: ...

    async def mark_used(self, raw_token: str) -> None: ...


class MissionOutcomeRepository(Protocol):
    async def get_by_mission_id(self, mission_id: UUID) -> MissionOutcome | None: ...

    async def save(self, outcome: MissionOutcome) -> None: ...


class AuditLogRepository(Protocol):
    async def add(
        self,
        *,
        id: UUID,
        actor_user_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: str | None,
        payload_json: str | None,
        request_id: str | None,
    ) -> None: ...

    async def list_page(
        self,
        offset: int,
        limit: int,
        *,
        q: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        actor_user_id: UUID | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[AuditLogEntry], int]: ...


class UsedQrJtiRepository(Protocol):
    """Anti-rejeu QR JWT: stocke les jti consommés (use-once)."""

    async def consume(self, *, jti: str, mission_id: UUID, consumed_at: datetime) -> bool:
        """Retourne False si déjà consommé."""


class AuditChainRepository(Protocol):
    """Chaîne hashée tamper-evident (MVP)."""

    async def append(
        self,
        *,
        created_at: datetime,
        resource_type: str,
        resource_id: str | None,
        entry_hash: str,
        prev_hash: str | None,
    ) -> None: ...
