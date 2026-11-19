"""FastAPI application factory."""

from fastapi import FastAPI

from homesure.api.logging_setup import setup_logging
from homesure.api.middleware import request_id_middleware
from homesure.api.routes import documents, health
from homesure.config import get_settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    setup_logging()

    app = FastAPI(title=settings.app_name)

    app.middleware("http")(request_id_middleware)

    app.include_router(health.router)
    app.include_router(documents.router)

    return app
