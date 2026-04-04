"""Throttling léger en mémoire (login / endpoints sensibles)."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

_lock = asyncio.Lock()
_buckets: dict[str, list[float]] = defaultdict(list)


async def enforce_rate_limit(request: Request, *, key_prefix: str, max_per_minute: int) -> None:
    if max_per_minute <= 0:
        return
    host = request.client.host if request.client else "unknown"
    key = f"{key_prefix}:{host}"
    now = time.monotonic()
    cutoff = now - 60.0
    async with _lock:
        bucket = _buckets[key]
        bucket[:] = [t for t in bucket if t > cutoff]
        if len(bucket) >= max_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Trop de requêtes. Réessayez dans une minute.",
            )
        bucket.append(now)
