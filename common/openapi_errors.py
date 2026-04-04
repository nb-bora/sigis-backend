"""Schéma d'erreur HTTP unifié pour OpenAPI."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Réponse d'erreur métier ou technique (alignée sur le handler `DomainError`)."""

    code: str = Field(..., description="Code stable d'erreur (ex. NOT_FOUND, FORBIDDEN).")
    message: str = Field(..., description="Message lisible humain.")
    request_id: str | None = Field(
        default=None,
        description="Identifiant de corrélation de la requête (si fourni par le middleware).",
    )
