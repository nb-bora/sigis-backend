from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from infrastructure.persistence.sqlalchemy.auth_repos import (
    PasswordResetTokenRepositoryImpl,
    UserAuthRepositoryImpl,
)
from infrastructure.persistence.sqlalchemy.extra_repos import (
    CoPresenceEventRepositoryImpl,
    ExceptionRequestRepositoryImpl,
    IdempotencyRepositoryImpl,
    PresenceProofRepositoryImpl,
)
from infrastructure.persistence.sqlalchemy.repositories_impl import (
    EstablishmentRepositoryImpl,
    MissionRepositoryImpl,
    SiteVisitRepositoryImpl,
)
from infrastructure.persistence.sqlalchemy.role_permission_repo import RolePermissionRepositoryImpl


class SqlAlchemyUnitOfWork:
    """Unit of Work — commit / rollback sur la session."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self.session: AsyncSession | None = None
        self.establishments: EstablishmentRepositoryImpl | None = None
        self.missions: MissionRepositoryImpl | None = None
        self.site_visits: SiteVisitRepositoryImpl | None = None
        self.presence_proofs: PresenceProofRepositoryImpl | None = None
        self.copresence_events: CoPresenceEventRepositoryImpl | None = None
        self.exception_requests: ExceptionRequestRepositoryImpl | None = None
        self.idempotency: IdempotencyRepositoryImpl | None = None
        self.users: UserAuthRepositoryImpl | None = None
        self.reset_tokens: PasswordResetTokenRepositoryImpl | None = None
        self.role_permissions: RolePermissionRepositoryImpl | None = None

    async def __aenter__(self) -> Self:
        self.session = self._session_factory()
        assert self.session is not None
        self.establishments = EstablishmentRepositoryImpl(self.session)
        self.missions = MissionRepositoryImpl(self.session)
        self.site_visits = SiteVisitRepositoryImpl(self.session)
        self.presence_proofs = PresenceProofRepositoryImpl(self.session)
        self.copresence_events = CoPresenceEventRepositoryImpl(self.session)
        self.exception_requests = ExceptionRequestRepositoryImpl(self.session)
        self.idempotency = IdempotencyRepositoryImpl(self.session)
        self.users = UserAuthRepositoryImpl(self.session)
        self.reset_tokens = PasswordResetTokenRepositoryImpl(self.session)
        self.role_permissions = RolePermissionRepositoryImpl(self.session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        if self.session is None:
            return
        if exc_type:
            await self.session.rollback()
        else:
            await self.session.commit()
        await self.session.close()
        self.session = None
        self.establishments = None
        self.missions = None
        self.site_visits = None
        self.presence_proofs = None
        self.copresence_events = None
        self.exception_requests = None
        self.idempotency = None
        self.users = None
        self.reset_tokens = None
        self.role_permissions = None
