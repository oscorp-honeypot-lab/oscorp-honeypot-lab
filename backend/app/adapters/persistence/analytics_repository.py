from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.analytics import (
    AnalyticsSummary,
    DownloadItem,
    EventListItem,
    Page,
    RiskScore,
    SessionDetail,
    SessionListItem,
)


class PostgresAnalyticsRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _session_item(row: Any) -> SessionListItem:
        return SessionListItem(
            session_key=row.session_key,
            session_id=row.session_id,
            sensor=row.sensor,
            src_ip=row.src_ip,
            src_port=row.src_port,
            first_event_at=row.first_event_at,
            last_event_at=row.last_event_at,
            duration_seconds=(
                float(row.duration_seconds)
                if row.duration_seconds is not None
                else None
            ),
            lifecycle_status=row.lifecycle_status,
            event_count=row.event_count,
            command_count=row.command_count,
            download_count=row.download_count,
            username=row.last_username or row.first_username,
            has_successful_login=row.has_successful_login,
            risk_score=row.risk_score,
            risk_level=row.risk_level,
        )

    @staticmethod
    def _event_item(row: Any) -> EventListItem:
        return EventListItem(
            id=row.id,
            timestamp=row.timestamp_evento,
            event_type=row.eventid,
            session_id=row.session_id,
            sensor=row.sensor,
            src_ip=row.src_ip,
            src_port=row.src_port,
            username=row.username,
            command=row.command_input,
            url=row.url,
            sha256=row.shasum,
        )

    async def summary(self, *, rules_version: str) -> AnalyticsSummary:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM eventos) AS events,
                        (SELECT COUNT(*) FROM sessions) AS sessions,
                        (
                            SELECT COUNT(DISTINCT src_ip)
                            FROM sessions
                            WHERE src_ip IS NOT NULL
                        ) AS unique_source_ips,
                        (
                            SELECT COUNT(*)
                            FROM sessions
                            WHERE has_successful_login
                        ) AS successful_login_sessions,
                        (
                            SELECT COUNT(*)
                            FROM sessions
                            WHERE has_download
                        ) AS download_sessions,
                        (
                            SELECT COUNT(*)
                            FROM session_risk_scores
                            WHERE rules_version = :rules_version
                              AND risk_level = 'low'
                        ) AS risk_low,
                        (
                            SELECT COUNT(*)
                            FROM session_risk_scores
                            WHERE rules_version = :rules_version
                              AND risk_level = 'medium'
                        ) AS risk_medium,
                        (
                            SELECT COUNT(*)
                            FROM session_risk_scores
                            WHERE rules_version = :rules_version
                              AND risk_level = 'high'
                        ) AS risk_high,
                        (
                            SELECT COUNT(*)
                            FROM session_risk_scores
                            WHERE rules_version = :rules_version
                              AND risk_level = 'critical'
                        ) AS risk_critical,
                        (SELECT MAX(timestamp_evento) FROM eventos) AS latest_event_at
                    """
                ),
                {"rules_version": rules_version},
            )
            row = result.one()
        return AnalyticsSummary(**row._mapping)

    async def list_sessions(
        self,
        *,
        page: int,
        page_size: int,
        rules_version: str,
    ) -> Page[SessionListItem]:
        offset = (page - 1) * page_size
        async with self._session_factory() as session:
            total = int(
                (
                    await session.execute(text("SELECT COUNT(*) FROM sessions"))
                ).scalar_one()
            )
            result = await session.execute(
                text(
                    """
                    SELECT
                        s.session_key,
                        s.session_id,
                        s.sensor,
                        s.src_ip,
                        s.src_port,
                        s.first_event_at,
                        s.last_event_at,
                        s.duration_seconds,
                        s.lifecycle_status,
                        s.event_count,
                        s.command_count,
                        s.download_count,
                        s.first_username,
                        s.last_username,
                        s.has_successful_login,
                        r.score AS risk_score,
                        r.risk_level
                    FROM sessions s
                    LEFT JOIN session_risk_scores r
                      ON r.session_key = s.session_key
                     AND r.rules_version = :rules_version
                    ORDER BY s.last_event_at DESC, s.session_key
                    LIMIT :limit OFFSET :offset
                    """
                ),
                {
                    "rules_version": rules_version,
                    "limit": page_size,
                    "offset": offset,
                },
            )
            items = tuple(self._session_item(row) for row in result)
        return Page(items=items, page=page, page_size=page_size, total=total)

    async def list_events(
        self,
        *,
        page: int,
        page_size: int,
    ) -> Page[EventListItem]:
        offset = (page - 1) * page_size
        async with self._session_factory() as session:
            total = int(
                (
                    await session.execute(text("SELECT COUNT(*) FROM eventos"))
                ).scalar_one()
            )
            result = await session.execute(
                text(
                    """
                    SELECT
                        id,
                        timestamp_evento,
                        eventid,
                        session_id,
                        sensor,
                        src_ip,
                        src_port,
                        username,
                        command_input,
                        url,
                        shasum
                    FROM eventos
                    ORDER BY timestamp_evento DESC NULLS LAST, id DESC
                    LIMIT :limit OFFSET :offset
                    """
                ),
                {"limit": page_size, "offset": offset},
            )
            items = tuple(self._event_item(row) for row in result)
        return Page(items=items, page=page, page_size=page_size, total=total)

    async def get_session(
        self,
        *,
        session_key: str,
        rules_version: str,
    ) -> SessionDetail | None:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    SELECT
                        s.session_key,
                        s.session_id,
                        s.sensor,
                        s.src_ip,
                        s.src_port,
                        s.first_event_at,
                        s.last_event_at,
                        s.duration_seconds,
                        s.lifecycle_status,
                        s.event_count,
                        s.command_count,
                        s.download_count,
                        s.first_username,
                        s.last_username,
                        s.has_successful_login,
                        r.score AS risk_score,
                        r.risk_level,
                        r.reasons,
                        r.rules_version,
                        r.calculated_at
                    FROM sessions s
                    LEFT JOIN session_risk_scores r
                      ON r.session_key = s.session_key
                     AND r.rules_version = :rules_version
                    WHERE s.session_key = :session_key
                    """
                ),
                {
                    "session_key": session_key,
                    "rules_version": rules_version,
                },
            )
            session_row = result.first()
            if session_row is None:
                return None

            events_result = await session.execute(
                text(
                    """
                    SELECT
                        id,
                        timestamp_evento,
                        eventid,
                        session_id,
                        sensor,
                        src_ip,
                        src_port,
                        username,
                        command_input,
                        url,
                        shasum
                    FROM eventos
                    WHERE COALESCE(sensor, 'unknown') = :sensor
                      AND session_id = :session_id
                    ORDER BY timestamp_evento, id
                    """
                ),
                {
                    "sensor": session_row.sensor,
                    "session_id": session_row.session_id,
                },
            )
            events = tuple(self._event_item(row) for row in events_result)

        score = None
        if session_row.risk_score is not None:
            score = RiskScore(
                score=session_row.risk_score,
                level=session_row.risk_level,
                reasons=tuple(session_row.reasons),
                rules_version=session_row.rules_version,
                calculated_at=session_row.calculated_at,
            )
        return SessionDetail(
            session=self._session_item(session_row),
            score=score,
            commands=tuple(
                event.command
                for event in events
                if event.event_type == "cowrie.command.input" and event.command
            ),
            downloads=tuple(
                DownloadItem(
                    timestamp=event.timestamp,
                    url=event.url,
                    sha256=event.sha256,
                )
                for event in events
                if event.event_type == "cowrie.session.file_download"
            ),
            events=events,
        )
