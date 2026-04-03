"""Mapping DomainError → réponses HTTP (couche présentation)."""

from fastapi import HTTPException, status

from domain.errors import DomainError


def domain_error_to_http(exc: DomainError) -> HTTPException:
    status_code = status.HTTP_400_BAD_REQUEST
    if exc.code in ("NOT_IMPLEMENTED",):
        status_code = status.HTTP_501_NOT_IMPLEMENTED
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})
