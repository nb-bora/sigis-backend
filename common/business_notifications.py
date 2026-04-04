"""
Notifications métier (stubs) — rappels mission, géofence, signalements.

En production : brancher SMTP déjà configuré ou file de jobs (Celery, etc.).
"""

from __future__ import annotations

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


async def notify_mission_reminder(mission_id: UUID, inspector_id: UUID) -> None:
    """Rappel avant fenêtre mission (non bloquant)."""
    logger.info(
        "[notify_mission_reminder] mission=%s inspector=%s (stub — pas d'envoi réel)",
        mission_id,
        inspector_id,
    )


async def notify_geofence_failure(mission_id: UUID, user_id: UUID, detail: str) -> None:
    """Échec géofence répété ou contestation (stub)."""
    logger.info(
        "[notify_geofence_failure] mission=%s user=%s detail=%s",
        mission_id,
        user_id,
        detail,
    )


async def notify_exception_resolved(exception_id: UUID, mission_id: UUID) -> None:
    """Signalement clôturé — retour terrain (stub)."""
    logger.info(
        "[notify_exception_resolved] exception=%s mission=%s",
        exception_id,
        mission_id,
    )


async def notify_mission_cancelled(mission_id: UUID, reason: str) -> None:
    """Mission annulée — parties prenantes (stub)."""
    logger.info("[notify_mission_cancelled] mission=%s reason=%s", mission_id, reason[:200])
