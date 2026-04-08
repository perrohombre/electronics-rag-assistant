"""Health check routes."""

from fastapi import APIRouter

from electronics_rag_assistant_backend.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Return a minimal service health response."""

    settings = get_settings()
    return {
        "status": "ok",
        "app_env": settings.app_env,
    }
