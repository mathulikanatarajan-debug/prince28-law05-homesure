"""Health-check routes."""

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    """Check whether the API is running."""
    return {"status": "ok"}


@router.get("/ready")
def readiness_check(request: Request) -> dict:
    """Check whether the application can access its data."""
    records_loaded = request.app.state.documents is not None
    if not records_loaded:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "checks": {"records_loaded": False},
            },
        )

    return {"status": "ready", "checks": {"records_loaded": True}}
