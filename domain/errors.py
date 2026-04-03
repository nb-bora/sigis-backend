"""Exceptions métier (à lever depuis le domaine, mapper en HTTP dans l'API)."""


class DomainError(Exception):
    """Erreur métier de base — codes stables à aligner avec le glossaire SIGIS."""

    code: str = "DOMAIN_ERROR"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code:
            self.code = code


class InvariantViolation(DomainError):
    code = "INVARIANT_VIOLATION"


class GeofenceRejected(DomainError):
    code = "OUTSIDE_GEOFENCE"


class CoPresenceRejected(DomainError):
    code = "COPRESENCE_REJECTED"


class MissionExpired(DomainError):
    code = "MISSION_EXPIRED"


class AlreadyCheckedOut(DomainError):
    code = "ALREADY_CHECKED_OUT"


class NotFound(DomainError):
    code = "NOT_FOUND"


class Conflict(DomainError):
    code = "CONFLICT"


class IdempotencyReplay(DomainError):
    code = "IDEMPOTENCY_REPLAY"


class Forbidden(DomainError):
    code = "FORBIDDEN"
