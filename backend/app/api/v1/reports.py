from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.dependencies import get_report_service, require_role, require_role_csrf
from app.api.schemas import ReportDeliveryResponse, ReportRunResponse
from app.application.report_service import (
    ReportDeliveryFailed,
    ReportFormatUnsupported,
    ReportNotFound,
    ReportService,
)
from app.domain.analytics import ReportArtifact
from app.domain.identity import Role, UserIdentity

router = APIRouter(prefix="/reports", tags=["reports"])
Viewer = Annotated[UserIdentity, Depends(require_role(Role.VIEWER))]
ViewerCsrf = Annotated[UserIdentity, Depends(require_role_csrf(Role.VIEWER))]
Service = Annotated[ReportService, Depends(get_report_service)]


def _download_response(artifact: ReportArtifact) -> Response:
    return Response(
        content=artifact.content,
        media_type=artifact.media_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{artifact.filename}"'
            ),
            "X-Report-ID": str(artifact.report_id),
            "X-Report-Delivery-ID": str(artifact.delivery_id),
            "X-Report-Period-Type": artifact.period_type,
        },
    )


@router.get("/latest/{period_type}", response_model=ReportRunResponse)
async def latest_report(
    period_type: str,
    _: Viewer,
    service: Service,
) -> ReportRunResponse:
    try:
        report = await service.latest(period_type=period_type)
    except ReportNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="report_not_found",
        ) from exc
    return ReportRunResponse.from_domain(report)


@router.get("/latest/{period_type}/download")
async def download_latest_report(
    period_type: str,
    actor: Viewer,
    service: Service,
    format: Annotated[str, Query(pattern=r"^(html|csv)$")] = "html",
) -> Response:
    try:
        artifact = await service.download_latest(
            actor=actor,
            period_type=period_type,
            format=format,
        )
    except ReportNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="report_not_found",
        ) from exc
    except ReportFormatUnsupported as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="report_format_unsupported",
        ) from exc
    return _download_response(artifact)


@router.post(
    "/latest/{period_type}/telegram",
    response_model=ReportDeliveryResponse,
)
async def send_latest_report_telegram(
    period_type: str,
    actor: ViewerCsrf,
    service: Service,
    format: Annotated[str, Query(pattern=r"^(html|csv)$")] = "html",
) -> ReportDeliveryResponse:
    try:
        delivery = await service.send_latest_telegram(
            actor=actor,
            period_type=period_type,
            format=format,
        )
    except ReportNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="report_not_found",
        ) from exc
    except ReportFormatUnsupported as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="report_format_unsupported",
        ) from exc
    except ReportDeliveryFailed as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="telegram_delivery_failed",
        ) from exc
    return ReportDeliveryResponse.from_domain(delivery)
