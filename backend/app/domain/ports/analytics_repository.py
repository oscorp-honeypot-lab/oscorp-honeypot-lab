from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.analytics import (
    AnalyticsSummary,
    EventFilters,
    EventListItem,
    Page,
    SessionDetail,
    SessionFilters,
    SessionListItem,
)


class AnalyticsRepository(Protocol):
    async def summary(self, *, rules_version: str) -> AnalyticsSummary: ...

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
