from __future__ import annotations

from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import structlog

from app.adapters.persistence.postgres_health_repository import (
    PostgresHealthRepository,
)
from app.api.v1.router import api_router
from app.application.health_service import HealthService
from app.infrastructure.config import get_settings
from app.infrastructure.database import create_engine, create_session_factory
from app.infrastructure.logging import configure_logging


settings = get_settings()
configure_logging(settings.log_level)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_engine(settings)
    repository = PostgresHealthRepository(create_session_factory(engine))
    app.state.health_service = HealthService(
        repository,
        service_name=settings.service_name,
        version=settings.version,
    )
    logger.info("api_started", environment=settings.environment)
    yield
    await engine.dispose()
    logger.info("api_stopped")


app = FastAPI(
    title="OSCORP ThreatLab API",
    summary="API operativa para análisis de sesiones SSH maliciosas.",
    version=settings.version,
    docs_url="/docs",
    redoc_url=None,
    openapi_url="/openapi.json",
    lifespan=lifespan,
)
app.include_router(api_router, prefix="/api/v1")


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid4()))
    started_at = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "request_failed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "internal_server_error", "request_id": request_id},
        )
    response.headers["x-request-id"] = request_id
    logger.info(
        "request_completed",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round((perf_counter() - started_at) * 1000, 2),
    )
    return response
