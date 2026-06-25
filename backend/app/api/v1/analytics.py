from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_analytics_service, require_role
from app.api.schemas import (
    AnalyticsSummaryResponse,
    EventPageResponse,
    SessionDetailResponse,
    SessionPageResponse,
)
from app.application.analytics_service import AnalyticsService, SessionNotFound
from app.domain.identity import Role, UserIdentity


router = APIRouter(tags=["analytics"])
Viewer = Annotated[UserIdentity, Depends(require_role(Role.VIEWER))]
Service = Annotated[AnalyticsService, Depends(get_analytics_service)]


@router.get("/analytics/summary", response_model=AnalyticsSummaryResponse)
async def summary(_: Viewer, service: Service) -> AnalyticsSummaryResponse:
    return AnalyticsSummaryResponse.from_domain(await service.summary())


@router.get("/sessions", response_model=SessionPageResponse)
async def sessions(
    _: Viewer,
    service: Service,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> SessionPageResponse:
    result = await service.list_sessions(page=page, page_size=page_size)
    return SessionPageResponse.from_domain(result)


@router.get("/events", response_model=EventPageResponse)
async def events(
    _: Viewer,
    service: Service,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> EventPageResponse:
    result = await service.list_events(page=page, page_size=page_size)
    return EventPageResponse.from_domain(result)


@router.get("/sessions/{session_key}", response_model=SessionDetailResponse)
async def session_detail(
    session_key: str,
    _: Viewer,
    service: Service,
) -> SessionDetailResponse:
    try:
        detail = await service.get_session(session_key)
    except SessionNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="session_not_found",
        ) from exc
    return SessionDetailResponse.from_domain(detail)
