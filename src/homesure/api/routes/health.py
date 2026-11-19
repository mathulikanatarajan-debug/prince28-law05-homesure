"""Health and readiness endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from homesure.api.deps import check_db

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Basic application health check."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(
    database: Annotated[bool, Depends(check_db)],
) -> dict[str, object]:
    """Check whether the application is ready to serve requests."""
    return {
        "status": "ready",
        "checks": {"database": database},
    }
