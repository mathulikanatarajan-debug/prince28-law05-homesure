"""Health-check routes."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    """Check whether the API is running."""
    return {"status": "healthy"}


@router.get("/ready")
def readiness_check() -> dict[str, str]:
    """Check whether the application can access its data."""
    return {"status": "ready"}
