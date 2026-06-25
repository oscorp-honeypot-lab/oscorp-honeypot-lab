from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.dependencies import get_export_service, require_role
from app.application.export_service import ExportFailed, ExportService
from app.domain.analytics import EventFilters, ExportArtifact, SessionFilters
from app.domain.identity import Role, UserIdentity


router = APIRouter(prefix="/exports", tags=["exports"])
Viewer = Annotated[UserIdentity, Depends(require_role(Role.VIEWER))]
Service = Annotated[ExportService, Depends(get_export_service)]


def _response(artifact: ExportArtifact) -> Response:
    return Response(
        content=artifact.content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{artifact.filename}"'
            ),
            "X-Export-ID": str(artifact.export_id),
            "X-Export-Row-Count": str(artifact.row_count),
            "X-Export-Total": str(artifact.total_rows),
            "X-Export-Page": str(artifact.page),
            "X-Export-Page-Size": str(artifact.page_size),
            "X-Export-Encoding": "utf-8-sig",
        },
    )


@router.get("/sessions.csv")
async def sessions_csv(
    actor: Viewer,
    service: Service,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=1000)] = 1000,
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
) -> Response:
    try:
        artifact = await service.sessions_csv(
            actor=actor,
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
            ),
        )
    except ExportFailed as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="export_failed",
        ) from exc
    return _response(artifact)


@router.get("/events.csv")
async def events_csv(
    actor: Viewer,
    service: Service,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=1000)] = 1000,
    from_at: Annotated[datetime | None, Query(alias="from")] = None,
    to_at: Annotated[datetime | None, Query(alias="to")] = None,
    src_ip: Annotated[str | None, Query(max_length=64)] = None,
    country: Annotated[str | None, Query(max_length=128)] = None,
    username: Annotated[str | None, Query(max_length=128)] = None,
    event_type: Annotated[str | None, Query(max_length=128)] = None,
) -> Response:
    try:
        artifact = await service.events_csv(
            actor=actor,
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
    except ExportFailed as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="export_failed",
        ) from exc
    return _response(artifact)
