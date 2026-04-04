"""Mapping DomainError → réponses HTTP (couche présentation)."""

from fastapi import HTTPException, status

from domain.errors import DomainError

_CODE_TO_STATUS: dict[str, int] = {
    "NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "CONFLICT": status.HTTP_409_CONFLICT,
    "IDEMPOTENCY_REPLAY": status.HTTP_409_CONFLICT,
    "FORBIDDEN": status.HTTP_403_FORBIDDEN,
    "UNAUTHORIZED": status.HTTP_401_UNAUTHORIZED,
    "INVALID_CREDENTIALS": status.HTTP_401_UNAUTHORIZED,
    "ACCOUNT_INACTIVE": status.HTTP_401_UNAUTHORIZED,
    "TOKEN_EXPIRED_OR_INVALID": status.HTTP_400_BAD_REQUEST,
    "EMAIL_ALREADY_EXISTS": status.HTTP_409_CONFLICT,
    "PHONE_ALREADY_EXISTS": status.HTTP_409_CONFLICT,
    "INVALID_PHONE_NUMBER": status.HTTP_422_UNPROCESSABLE_CONTENT,
    "OUTSIDE_GEOFENCE": status.HTTP_400_BAD_REQUEST,
    "COPRESENCE_REJECTED": status.HTTP_400_BAD_REQUEST,
    "MISSION_EXPIRED": status.HTTP_400_BAD_REQUEST,
    "ALREADY_CHECKED_OUT": status.HTTP_400_BAD_REQUEST,
    "INVARIANT_VIOLATION": status.HTTP_422_UNPROCESSABLE_CONTENT,
    "NOT_IMPLEMENTED": status.HTTP_501_NOT_IMPLEMENTED,
    "HOST_NOT_AUTHORIZED": status.HTTP_403_FORBIDDEN,
    "MISSION_APPROVAL_REQUIRED": status.HTTP_409_CONFLICT,
}


def domain_error_to_http(exc: Exception) -> HTTPException:
    if not isinstance(exc, DomainError):
        raise exc
    status_code = _CODE_TO_STATUS.get(exc.code, status.HTTP_400_BAD_REQUEST)
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})
