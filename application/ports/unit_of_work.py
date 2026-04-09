"""Unit of Work — transaction unique par cas d'usage."""

from __future__ import annotations

from typing import Protocol

from application.ports.repositories import (
    AuditChainRepository,
    AuditLogRepository,
    CoPresenceEventRepository,
    EstablishmentRepository,
    ExceptionRequestRepository,
    IdempotencyRepository,
    MissionOutcomeRepository,
    MissionRepository,
    PasswordResetTokenRepository,
    PresenceProofRepository,
    SiteVisitRepository,
    UsedQrJtiRepository,
    UserRepository,
)


class UnitOfWork(Protocol):
    establishments: EstablishmentRepository
    missions: MissionRepository
    site_visits: SiteVisitRepository
    presence_proofs: PresenceProofRepository
    copresence_events: CoPresenceEventRepository
    exception_requests: ExceptionRequestRepository
    idempotency: IdempotencyRepository
    users: UserRepository
    reset_tokens: PasswordResetTokenRepository
    mission_outcomes: MissionOutcomeRepository
    audit_logs: AuditLogRepository
    used_qr_jti: UsedQrJtiRepository
    audit_chain: AuditChainRepository

    async def __aenter__(self) -> UnitOfWork: ...

    async def __aexit__(self, *args: object) -> None: ...
