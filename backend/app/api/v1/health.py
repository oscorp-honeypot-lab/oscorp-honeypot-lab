from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_health_service
from app.api.schemas import HealthResponse
from app.application.health_service import HealthService
from app.domain.health import HealthStatus


router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=HealthResponse)
def live(
    service: Annotated[HealthService, Depends(get_health_service)],
) -> HealthResponse:
    return HealthResponse.from_domain(service.live())


@router.get(
    "/ready",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse}},
)
async def ready(
    response: Response,
    service: Annotated[HealthService, Depends(get_health_service)],
) -> HealthResponse:
    health = await service.ready()
    if health.status is HealthStatus.DEGRADED:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse.from_domain(health)
