"""ASGI entrypoint for the backend application."""

from electronics_rag_assistant_backend.api.app import create_app

app = create_app()
