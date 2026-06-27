from __future__ import annotations

from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.adapters.persistence.analytics_repository import (
    PostgresAnalyticsRepository,
)
from app.adapters.persistence.identity_repository import (
    PostgresIdentityRepository,
)
from app.adapters.persistence.postgres_health_repository import (
    PostgresHealthRepository,
)
from app.api.middleware.security import CsrfMiddleware, SecurityHeadersMiddleware
from app.api.v1.router import api_router
from app.application.analytics_service import AnalyticsService
from app.application.auth_service import AuthService
from app.application.export_service import ExportService
from app.application.health_service import HealthService
from app.application.lab_service import LabService
from app.application.report_service import ReportService
from app.infrastructure.config import get_settings
from app.infrastructure.database import create_engine, create_session_factory
from app.infrastructure.logging import configure_logging
from app.infrastructure.security import PasswordManager
from app.infrastructure.telegram import TelegramAdapter

settings = get_settings()
configure_logging(settings.log_level)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    repository = PostgresHealthRepository(session_factory)
    app.state.health_service = HealthService(
        repository,
        service_name=settings.service_name,
        version=settings.version,
    )
    app.state.auth_service = AuthService(
        PostgresIdentityRepository(session_factory),
        PasswordManager(),
        session_absolute_minutes=settings.session_absolute_minutes,
        session_idle_minutes=settings.session_idle_minutes,
        login_window_minutes=settings.login_window_minutes,
        login_max_failures=settings.login_max_failures,
    )
    analytics_repository = PostgresAnalyticsRepository(session_factory)
    app.state.analytics_service = AnalyticsService(
        analytics_repository,
        rules_version="1.1.0",
    )
    app.state.export_service = ExportService(
        analytics_repository,
        rules_version="1.1.0",
    )
    app.state.report_service = ReportService(
        analytics_repository,
        telegram_sender=TelegramAdapter.from_settings(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
        ),
    )
    app.state.lab_service = LabService(
        analytics_repository,
        environment=settings.environment,
        lab_runner_url=settings.lab_runner_url,
        pipeline_worker_url=settings.pipeline_worker_url,
    )
    app.state.settings = settings
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "X-Request-ID"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CsrfMiddleware,
    session_cookie_name=settings.session_cookie_name,
    csrf_cookie_name=settings.csrf_cookie_name,
    exempt_paths={"/api/v1/auth/login"},
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
