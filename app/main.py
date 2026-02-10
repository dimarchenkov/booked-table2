"""FastAPI application entrypoint."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.admin.admin import setup_admin
from app.admin.poster import router as poster_router
from app.api.routes import router as api_router
from app.core.config import get_settings

settings = get_settings()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key="admin-secret")
    app.include_router(api_router)
    app.include_router(poster_router)
    setup_admin(app)
    return app


app = create_app()
