from __future__ import annotations

from app.domain.analytics import (
    AnalyticsSummary,
    EventListItem,
    Page,
    SessionDetail,
    SessionListItem,
)
from app.domain.ports.analytics_repository import AnalyticsRepository


class SessionNotFound(Exception):
    pass


class AnalyticsService:
    def __init__(
        self,
        repository: AnalyticsRepository,
        *,
        rules_version: str,
    ) -> None:
        self._repository = repository
        self._rules_version = rules_version

    async def summary(self) -> AnalyticsSummary:
        return await self._repository.summary(rules_version=self._rules_version)

    async def list_sessions(
        self,
        *,
        page: int,
        page_size: int,
    ) -> Page[SessionListItem]:
        return await self._repository.list_sessions(
            page=page,
            page_size=page_size,
            rules_version=self._rules_version,
        )

    async def list_events(
        self,
        *,
        page: int,
        page_size: int,
    ) -> Page[EventListItem]:
        return await self._repository.list_events(page=page, page_size=page_size)

    async def get_session(self, session_key: str) -> SessionDetail:
        detail = await self._repository.get_session(
            session_key=session_key,
            rules_version=self._rules_version,
        )
        if detail is None:
            raise SessionNotFound
        return detail
