from fastapi import APIRouter

router = APIRouter(tags=["health"])

@router.get("/health")
async def health() -> dict[str, str]:
    """Return a lightweight liveness response without checking external services."""
    return {
        "status": "ok",
        "service": "AI Therapy Coach Backend",
    }
