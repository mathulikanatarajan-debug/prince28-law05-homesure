"""FastAPI application factory."""

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from homesure.api.logging_setup import setup_logging
from homesure.api.middleware import request_id_middleware
from homesure.api.routes import documents, health
from homesure.config import Settings, get_settings
from homesure.db.session import make_engine, make_sessionmaker

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = settings or get_settings()
    setup_logging(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = make_engine(settings)
        app.state.engine = engine
        app.state.session_factory = make_sessionmaker(engine)

        try:
            try:
                with settings.data_file.open(encoding="utf-8") as file:
                    app.state.documents = json.load(file)
            except (OSError, json.JSONDecodeError):
                app.state.documents = None
                logger.exception("Could not load records from %s", settings.data_file)

            yield
        finally:
            await engine.dispose()

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.dependency_overrides[get_settings] = lambda: settings

    app.middleware("http")(request_id_middleware)

    app.include_router(health.router)
    app.include_router(documents.router)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        title = "Not Found" if exc.status_code == 404 else "HTTP Error"

        return JSONResponse(
            status_code=exc.status_code,
            media_type="application/problem+json",
            content={
                "type": "about:blank",
                "title": title,
                "status": exc.status_code,
                "detail": exc.detail,
                "request_id": request.state.request_id,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = [
            {
                "field": ".".join(str(part) for part in error["loc"]),
                "message": error["msg"],
            }
            for error in exc.errors()
        ]

        return JSONResponse(
            status_code=422,
            media_type="application/problem+json",
            content={
                "type": "about:blank",
                "title": "Unprocessable Entity",
                "status": 422,
                "errors": errors,
                "request_id": request.state.request_id,
            },
        )

    return app
