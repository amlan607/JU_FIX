"""FastAPI application factory for the JU_FIX monolith.

The application is one deployable unit (Architecture 1.2). Feature controllers
are discovered from ``app.controllers`` and mounted under a single ``/api`` prefix.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers import collect_routers
from app.core.config import settings
from app.core.database import init_db
from app.core.errors import register_exception_handlers
from app.core.responses import success_response

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

API_PREFIX = "/api"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Create database tables on startup for local development and CI runs.

    Production migrations are handled separately; this hook only guarantees that
    a freshly cloned checkout can start without a manual schema step.
    """
    init_db()
    yield


def create_app() -> FastAPI:
    """Build and configure the JU_FIX FastAPI application.

    Returns:
        FastAPI: The fully configured application instance.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description=(
            "Monolithic MVC backend for the Jahangirnagar University Medical Centre "
            "Automation System. All responses use the envelope "
            '{"success": bool, "data": object, "error": object}.'
        ),
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    for router in collect_routers():
        app.include_router(router, prefix=API_PREFIX)

    @app.get("/api/health", tags=["System"])
    def health_check() -> dict:
        """Report that the API process is running."""
        return success_response({"status": "ok", "environment": settings.ENVIRONMENT})

    return app


app = create_app()
