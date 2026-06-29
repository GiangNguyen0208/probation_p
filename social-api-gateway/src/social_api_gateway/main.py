"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from .admin.platforms.routes import router as platform_admin_router
from .admin.routes import router as admin_router
from .alerts.routes import router as alerts_router
from .config import get_settings
from .db import dispose_engine
from .errors import register_exception_handlers
from .health.routes import router as health_router
from .logging_setup import configure_logging, get_logger
from .subjects.routes import router as subjects_router
from .telegram.routes import router as telegram_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.runtime.log_level)
    logger = get_logger("social_api_gateway.main")
    logger.info("gateway.starting", env=settings.runtime.environment)

    # Startup validation: check Platform enum against platforms table.
    try:
        from sqlalchemy import select as sa_select

        from .admin.platforms.models import PlatformModel
        from .db import get_engine, get_session_factory

        engine = get_engine(settings.database)
        session_factory = get_session_factory(engine)
        async with session_factory() as session:
            result = await session.execute(
                sa_select(PlatformModel.slug).where(PlatformModel.is_active.is_(True))
            )
            db_slugs = {row[0] for row in result.all()}
        from social_common.enums import Platform

        code_slugs = {m.value for m in Platform}

        missing_in_db = code_slugs - db_slugs
        missing_in_code = db_slugs - code_slugs

        if missing_in_db:
            logger.warning(
                "platform.mismatch.db_missing",
                slugs=sorted(missing_in_db),
            )
        if missing_in_code:
            logger.warning(
                "platform.mismatch.code_missing",
                slugs=sorted(missing_in_code),
            )
        if not missing_in_db and not missing_in_code:
            logger.info("platform.validation.ok", platforms=sorted(db_slugs))
    except Exception as exc:  # noqa: BLE001
        logger.warning("platform.validation.skipped", error=str(exc))

    try:
        yield
    finally:
        await dispose_engine()
        logger.info("gateway.stopped")


def _custom_openapi(app: FastAPI) -> dict[str, Any]:
    """Build an OpenAPI schema that advertises the gateway's security schemes.

    Two schemes are registered:
    - `APIKeyAuth`: X-API-Key header (default for normal endpoints)
    - `AdminAuth`: Bearer token (used by /v1/admin/* routes, which
      override the global security per-route via `openapi_extra`)

    Without this, Swagger UI does not show the "Authorize" button
    because the spec has no security schemes defined.
    """
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )

    security_schemes = schema.setdefault("components", {}).setdefault("securitySchemes", {})
    security_schemes["APIKeyAuth"] = {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": (
            "API key issued via the admin endpoint. Internal keys have higher rate "
            "limits; external keys are read-only. The raw key is shown exactly "
            "once at creation time."
        ),
    }
    security_schemes["AdminAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "description": (
            "Admin token from the ADMIN_TOKEN env var. Used only by the "
            "/v1/admin/* endpoints. A compromised regular API key cannot be "
            "used to mint more keys."
        ),
    }
    # Global default: all routes require X-API-Key unless they override
    # it (e.g. /v1/admin/keys uses openapi_extra to require AdminAuth).
    schema["security"] = [{"APIKeyAuth": []}]

    app.openapi_schema = schema
    return schema


def create_app() -> FastAPI:
    app = FastAPI(
        title="Social Intelligence Platform API",
        description=(
            "Public REST API for the Social Intelligence Platform. "
            "All endpoints require a valid API key. Internal keys have "
            "higher rate limits and (in Sprint 2) access to write endpoints; "
            "external keys are read-only and rate-limited."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.openapi = lambda: _custom_openapi(app)  # type: ignore[method-assign]

    app.include_router(health_router)
    app.include_router(subjects_router)
    app.include_router(alerts_router)
    app.include_router(admin_router)
    app.include_router(platform_admin_router)
    app.include_router(telegram_router)

    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    return app


app = create_app()
