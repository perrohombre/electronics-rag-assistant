"""FastAPI application factory."""

from fastapi import FastAPI

from electronics_rag_assistant_backend.api.routes.assistant import router as assistant_router
from electronics_rag_assistant_backend.api.routes.catalog import router as catalog_router
from electronics_rag_assistant_backend.api.routes.health import router as health_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="Electronics RAG Assistant API",
        version="0.1.0",
        summary="Backend API for the electronics shopping assistant prototype.",
    )
    app.include_router(health_router)
    app.include_router(catalog_router)
    app.include_router(assistant_router)
    return app
