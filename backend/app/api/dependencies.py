from __future__ import annotations

from fastapi import Request

from app.application.health_service import HealthService


def get_health_service(request: Request) -> HealthService:
    return request.app.state.health_service
