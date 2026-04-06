from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version

from fastapi import APIRouter

router = APIRouter(tags=["health"])


def _distribution_version() -> str:
    try:
        return package_version("sigis-backend")
    except PackageNotFoundError:
        return "0.1.0"


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "sigis-backend",
        "version": _distribution_version(),
    }
