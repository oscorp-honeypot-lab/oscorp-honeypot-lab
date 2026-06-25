from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_analytics_service, require_role
from app.api.schemas import AlertPageResponse
from app.application.analytics_service import AnalyticsService
from app.domain.identity import Role, UserIdentity


router = APIRouter(prefix="/alerts", tags=["alerts"])

Viewer = Annotated[UserIdentity, Depends(require_role(Role.VIEWER))]
Service = Annotated[AnalyticsService, Depends(get_analytics_service)]


@router.get("", response_model=AlertPageResponse)
async def list_alerts(
    _: Viewer,
    service: Service,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200, alias="pageSize")] = 50,
    status: Annotated[str | None, Query()] = None,
    session_key: Annotated[str | None, Query(alias="sessionKey")] = None,
) -> AlertPageResponse:
    result = await service.list_alerts(
        page=page,
        page_size=page_size,
        status=status,
        session_key=session_key,
    )
    return AlertPageResponse.from_domain(result)
