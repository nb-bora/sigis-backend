"""Paramètres et enveloppes de pagination pour l'API."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageParams(BaseModel):
    """Query `skip` / `limit` (limit plafonné côté route)."""

    skip: int = Field(0, ge=0, description="Nombre d'éléments à sauter.")
    limit: int = Field(50, ge=1, le=500, description="Taille de page (max 500).")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int
