from __future__ import annotations

from typing import Annotated

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.dependencies import (
    client_ip,
    get_analytics_service,
    require_role,
    require_role_csrf,
    user_agent,
)
from app.api.schemas import (
    AnalyticsSummaryResponse,
    EventPageResponse,
    GeoStatsResponse,
    MttdStatsResponse,
    SessionDetailResponse,
    SessionListItemResponse,
    SessionPageResponse,
    SessionReviewRequest,
    TimelineResponse,
    VtStatsResponse,
)
from app.application.analytics_service import AnalyticsService, SessionNotFound
from app.domain.analytics import EventFilters, SessionFilters
from app.domain.identity import Role, UserIdentity


router = APIRouter(tags=["analytics"])
Viewer = Annotated[UserIdentity, Depends(require_role(Role.VIEWER))]
Service = Annotated[AnalyticsService, Depends(get_analytics_service)]
AnalystCsrf = Annotated[
    UserIdentity,
    Depends(require_role_csrf(Role.ANALYST)),
]


@router.get("/analytics/summary", response_model=AnalyticsSummaryResponse)
async def summary(_: Viewer, service: Service) -> AnalyticsSummaryResponse:
    return AnalyticsSummaryResponse.from_domain(await service.summary())


@router.get("/analytics/timeline", response_model=TimelineResponse)
async def timeline(
    _: Viewer,
    service: Service,
    hours: Annotated[int, Query(ge=1, le=720)] = 24,
) -> TimelineResponse:
    points = await service.timeline(hours=hours)
    return TimelineResponse.from_domain(hours=hours, points=points)


@router.get("/analytics/mttd", response_model=MttdStatsResponse)
async def mttd_stats(_: Viewer, service: Service) -> MttdStatsResponse:
    stats = await service.get_mttd_stats()
    return MttdStatsResponse.from_domain(stats)


@router.get("/analytics/vt-stats", response_model=VtStatsResponse)
async def vt_stats(_: Viewer, service: Service) -> VtStatsResponse:
    stats = await service.get_vt_stats()
    return VtStatsResponse.from_domain(stats)


@router.get("/analytics/geo-stats", response_model=GeoStatsResponse)
async def geo_stats(_: Viewer, service: Service) -> GeoStatsResponse:
    stats = await service.get_geo_stats()
    return GeoStatsResponse.from_domain(stats)


@router.get("/sessions", response_model=SessionPageResponse)
async def sessions(
    _: Viewer,
    service: Service,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    from_at: Annotated[datetime | None, Query(alias="from")] = None,
    to_at: Annotated[datetime | None, Query(alias="to")] = None,
    src_ip: Annotated[str | None, Query(max_length=64)] = None,
    country: Annotated[str | None, Query(max_length=128)] = None,
    username: Annotated[str | None, Query(max_length=128)] = None,
    event_type: Annotated[str | None, Query(max_length=128)] = None,
    risk_level: Annotated[
        str | None,
        Query(pattern=r"^(low|medium|high|critical)$"),
    ] = None,
    reviewed: bool | None = None,
    sort_by: Annotated[
        str,
        Query(
            pattern=(
                r"^(last_event_at|risk_score|event_count|command_count|"
                r"download_count|src_ip|country)$"
            )
        ),
    ] = "last_event_at",
    sort_order: Annotated[str, Query(pattern=r"^(asc|desc)$")] = "desc",
) -> SessionPageResponse:
    result = await service.list_sessions(
        page=page,
        page_size=page_size,
        filters=SessionFilters(
            from_at=from_at,
            to_at=to_at,
            src_ip=src_ip,
            country=country,
            username=username,
            event_type=event_type,
            risk_level=risk_level,
            reviewed=reviewed,
            sort_by=sort_by,
            sort_order=sort_order,
        ),
    )
    return SessionPageResponse.from_domain(result)


@router.get("/events", response_model=EventPageResponse)
async def events(
    _: Viewer,
    service: Service,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    from_at: Annotated[datetime | None, Query(alias="from")] = None,
    to_at: Annotated[datetime | None, Query(alias="to")] = None,
    src_ip: Annotated[str | None, Query(max_length=64)] = None,
    country: Annotated[str | None, Query(max_length=128)] = None,
    username: Annotated[str | None, Query(max_length=128)] = None,
    event_type: Annotated[str | None, Query(max_length=128)] = None,
) -> EventPageResponse:
    result = await service.list_events(
        page=page,
        page_size=page_size,
        filters=EventFilters(
            from_at=from_at,
            to_at=to_at,
            src_ip=src_ip,
            country=country,
            username=username,
            event_type=event_type,
        ),
    )
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


@router.patch(
    "/sessions/{session_key}/review",
    response_model=SessionListItemResponse,
)
async def review_session(
    session_key: str,
    payload: SessionReviewRequest,
    request: Request,
    actor: AnalystCsrf,
    service: Service,
) -> SessionListItemResponse:
    try:
        session = await service.set_session_review(
            session_key=session_key,
            reviewed=payload.reviewed,
            actor=actor,
            client_ip=client_ip(request),
            user_agent=user_agent(request),
        )
    except SessionNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="session_not_found",
        ) from exc
    return SessionListItemResponse.model_validate(session)
