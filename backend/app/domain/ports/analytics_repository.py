from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.analytics import (
    AlertItem,
    AnalyticsSummary,
    EventFilters,
    EventListItem,
    GeoStats,
    MttdStats,
    Page,
    ReportRun,
    SessionDetail,
    SessionFilters,
    SessionListItem,
    TimelinePoint,
    VtStats,
)


class AnalyticsRepository(Protocol):
    async def summary(self, *, rules_version: str) -> AnalyticsSummary: ...

    async def timeline(self, *, hours: int) -> tuple[TimelinePoint, ...]: ...

    async def list_sessions(
        self,
        *,
        page: int,
        page_size: int,
        rules_version: str,
        filters: SessionFilters,
    ) -> Page[SessionListItem]: ...

    async def list_events(
        self,
        *,
        page: int,
        page_size: int,
        filters: EventFilters,
    ) -> Page[EventListItem]: ...

    async def get_session(
        self,
        *,
        session_key: str,
        rules_version: str,
    ) -> SessionDetail | None: ...

    async def get_mttd_stats(self) -> MttdStats: ...

    async def get_vt_stats(self) -> VtStats: ...

    async def get_geo_stats(self) -> GeoStats: ...

    async def list_alerts(
        self,
        *,
        page: int,
        page_size: int,
        status: str | None = None,
        session_key: str | None = None,
    ) -> Page[AlertItem]: ...

    async def set_session_review(
        self,
        *,
        session_key: str,
        reviewed: bool,
        actor_id: UUID,
        client_ip: str,
        user_agent: str,
    ) -> SessionListItem | None: ...

    async def start_export(
        self,
        *,
        user_id: UUID,
        resource: str,
        page: int,
        page_size: int,
        filters: dict[str, object],
        encoding: str,
    ) -> UUID: ...

    async def complete_export(
        self,
        *,
        export_id: UUID,
        row_count: int,
        total_rows: int,
        filename: str,
    ) -> None: ...

    async def fail_export(
        self,
        *,
        export_id: UUID,
        error_code: str,
    ) -> None: ...

    async def get_latest_report(
        self,
        *,
        period_type: str,
    ) -> ReportRun | None: ...

    async def start_report_delivery(
        self,
        *,
        report_id: UUID,
        user_id: UUID,
        channel: str,
        format: str,
    ) -> UUID: ...

    async def finish_report_delivery(
        self,
        *,
        delivery_id: UUID,
        status: str,
        filename: str | None = None,
        error_code: str | None = None,
        error_detail: str | None = None,
    ) -> None: ...
