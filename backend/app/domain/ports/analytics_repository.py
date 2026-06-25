from __future__ import annotations

from typing import Protocol

from app.domain.analytics import (
    AnalyticsSummary,
    EventListItem,
    Page,
    SessionDetail,
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
    ) -> Page[SessionListItem]: ...

    async def list_events(
        self,
        *,
        page: int,
        page_size: int,
    ) -> Page[EventListItem]: ...

    async def get_session(
        self,
        *,
        session_key: str,
        rules_version: str,
    ) -> SessionDetail | None: ...
