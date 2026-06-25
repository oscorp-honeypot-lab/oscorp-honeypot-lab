from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.analytics import (
    AlertItem,
    AnalyticsSummary,
    DownloadItem,
    EventFilters,
    EventListItem,
    Page,
    RiskScore,
    SessionDetail,
    SessionFilters,
    SessionListItem,
    TimelinePoint,
)


COUNTRY_EXPRESSION = """
COALESCE(
    e.raw_event ->> 'country',
    e.raw_event ->> 'country_name',
    e.raw_event #>> '{geo,country}',
    e.raw_event #>> '{geo,country_name}',
    e.raw_event #>> '{geoip,country}',
    e.raw_event #>> '{geoip,country_name}'
)
"""

SESSION_SELECT = f"""
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
    (
        SELECT {COUNTRY_EXPRESSION}
        FROM eventos e
        WHERE COALESCE(e.sensor, 'unknown') = s.sensor
          AND e.session_id = s.session_id
          AND {COUNTRY_EXPRESSION} IS NOT NULL
        ORDER BY e.timestamp_evento, e.id
        LIMIT 1
    ) AS country,
    r.score AS risk_score,
    r.risk_level,
    s.reviewed,
    s.reviewed_at,
    s.reviewed_by,
    reviewer.username AS reviewed_by_username
FROM sessions s
LEFT JOIN session_risk_scores r
  ON r.session_key = s.session_key
 AND r.rules_version = :rules_version
LEFT JOIN app_users reviewer ON reviewer.id = s.reviewed_by
"""

EVENT_SELECT = f"""
SELECT
    e.id,
    e.timestamp_evento,
    e.eventid,
    e.session_id,
    e.sensor,
    e.src_ip,
    e.src_port,
    e.username,
    e.command_input,
    e.url,
    e.shasum,
    {COUNTRY_EXPRESSION} AS country
FROM eventos e
"""

SESSION_SORT_EXPRESSIONS = {
    "last_event_at": "s.last_event_at",
    "risk_score": "r.score",
    "event_count": "s.event_count",
    "command_count": "s.command_count",
    "download_count": "s.download_count",
    "src_ip": "s.src_ip",
    "country": "country",
}


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
            country=row.country,
            risk_score=row.risk_score,
            risk_level=row.risk_level,
            reviewed=row.reviewed,
            reviewed_at=row.reviewed_at,
            reviewed_by=row.reviewed_by,
            reviewed_by_username=row.reviewed_by_username,
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
            country=row.country,
        )

    @staticmethod
    def _session_filter_sql(
        filters: SessionFilters,
    ) -> tuple[str, dict[str, object]]:
        clauses: list[str] = []
        params: dict[str, object] = {}
        if filters.from_at is not None:
            clauses.append("s.last_event_at >= :from_at")
            params["from_at"] = filters.from_at
        if filters.to_at is not None:
            clauses.append("s.first_event_at <= :to_at")
            params["to_at"] = filters.to_at
        if filters.src_ip:
            clauses.append("s.src_ip = :src_ip")
            params["src_ip"] = filters.src_ip
        if filters.username:
            clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM eventos eu
                    WHERE COALESCE(eu.sensor, 'unknown') = s.sensor
                      AND eu.session_id = s.session_id
                      AND LOWER(eu.username) = LOWER(:username)
                )
                """
            )
            params["username"] = filters.username
        if filters.event_type:
            clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM eventos et
                    WHERE COALESCE(et.sensor, 'unknown') = s.sensor
                      AND et.session_id = s.session_id
                      AND et.eventid = :event_type
                )
                """
            )
            params["event_type"] = filters.event_type
        if filters.country:
            clauses.append(
                f"""
                EXISTS (
                    SELECT 1
                    FROM eventos ec
                    WHERE COALESCE(ec.sensor, 'unknown') = s.sensor
                      AND ec.session_id = s.session_id
                      AND LOWER(
                          COALESCE(
                              ec.raw_event ->> 'country',
                              ec.raw_event ->> 'country_name',
                              ec.raw_event #>> '{{geo,country}}',
                              ec.raw_event #>> '{{geo,country_name}}',
                              ec.raw_event #>> '{{geoip,country}}',
                              ec.raw_event #>> '{{geoip,country_name}}'
                          )
                      ) = LOWER(:country)
                )
                """
            )
            params["country"] = filters.country
        if filters.risk_level:
            clauses.append("r.risk_level = :risk_level")
            params["risk_level"] = filters.risk_level
        if filters.reviewed is not None:
            clauses.append("s.reviewed = :reviewed")
            params["reviewed"] = filters.reviewed
        return (
            " WHERE " + " AND ".join(clauses) if clauses else "",
            params,
        )

    @staticmethod
    def _event_filter_sql(
        filters: EventFilters,
    ) -> tuple[str, dict[str, object]]:
        clauses: list[str] = []
        params: dict[str, object] = {}
        if filters.from_at is not None:
            clauses.append("e.timestamp_evento >= :from_at")
            params["from_at"] = filters.from_at
        if filters.to_at is not None:
            clauses.append("e.timestamp_evento <= :to_at")
            params["to_at"] = filters.to_at
        if filters.src_ip:
            clauses.append("e.src_ip = :src_ip")
            params["src_ip"] = filters.src_ip
        if filters.username:
            clauses.append("LOWER(e.username) = LOWER(:username)")
            params["username"] = filters.username
        if filters.event_type:
            clauses.append("e.eventid = :event_type")
            params["event_type"] = filters.event_type
        if filters.country:
            clauses.append(
                f"LOWER({COUNTRY_EXPRESSION}) = LOWER(:country)"
            )
            params["country"] = filters.country
        return (
            " WHERE " + " AND ".join(clauses) if clauses else "",
            params,
        )

    @staticmethod
    def _session_order_sql(filters: SessionFilters) -> str:
        expression = SESSION_SORT_EXPRESSIONS[filters.sort_by]
        direction = filters.sort_order.upper()
        return (
            f" ORDER BY {expression} {direction} NULLS LAST, "
            "s.session_key ASC"
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

    async def timeline(self, *, hours: int) -> tuple[TimelinePoint, ...]:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    WITH bounds AS (
                        SELECT
                            date_trunc('hour', NOW())
                            - make_interval(hours => :hours - 1) AS start_at,
                            date_trunc('hour', NOW()) AS end_at
                    ),
                    buckets AS (
                        SELECT generate_series(
                            bounds.start_at,
                            bounds.end_at,
                            INTERVAL '1 hour'
                        ) AS bucket
                        FROM bounds
                    ),
                    event_counts AS (
                        SELECT
                            date_trunc('hour', timestamp_evento) AS bucket,
                            COUNT(*)::integer AS events
                        FROM eventos, bounds
                        WHERE timestamp_evento >= bounds.start_at
                          AND timestamp_evento < bounds.end_at + INTERVAL '1 hour'
                        GROUP BY 1
                    ),
                    session_counts AS (
                        SELECT
                            date_trunc('hour', first_event_at) AS bucket,
                            COUNT(*)::integer AS sessions
                        FROM sessions, bounds
                        WHERE first_event_at >= bounds.start_at
                          AND first_event_at < bounds.end_at + INTERVAL '1 hour'
                        GROUP BY 1
                    )
                    SELECT
                        buckets.bucket,
                        COALESCE(event_counts.events, 0) AS events,
                        COALESCE(session_counts.sessions, 0) AS sessions
                    FROM buckets
                    LEFT JOIN event_counts USING (bucket)
                    LEFT JOIN session_counts USING (bucket)
                    ORDER BY buckets.bucket
                    """
                ),
                {"hours": hours},
            )
            return tuple(
                TimelinePoint(
                    timestamp=row.bucket,
                    events=row.events,
                    sessions=row.sessions,
                )
                for row in result
            )

    async def list_sessions(
        self,
        *,
        page: int,
        page_size: int,
        rules_version: str,
        filters: SessionFilters,
    ) -> Page[SessionListItem]:
        offset = (page - 1) * page_size
        where_sql, params = self._session_filter_sql(filters)
        order_sql = self._session_order_sql(filters)
        params["rules_version"] = rules_version
        async with self._session_factory() as session:
            total_result = await session.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM sessions s
                    LEFT JOIN session_risk_scores r
                      ON r.session_key = s.session_key
                     AND r.rules_version = :rules_version
                    """
                    + where_sql
                ),
                params,
            )
            total = int(total_result.scalar_one())
            result = await session.execute(
                text(
                    SESSION_SELECT
                    + where_sql
                    + order_sql
                    + """
                    LIMIT :limit OFFSET :offset
                    """
                ),
                {**params, "limit": page_size, "offset": offset},
            )
            items = tuple(self._session_item(row) for row in result)
        return Page(items=items, page=page, page_size=page_size, total=total)

    async def list_events(
        self,
        *,
        page: int,
        page_size: int,
        filters: EventFilters,
    ) -> Page[EventListItem]:
        offset = (page - 1) * page_size
        where_sql, params = self._event_filter_sql(filters)
        async with self._session_factory() as session:
            total_result = await session.execute(
                text("SELECT COUNT(*) FROM eventos e" + where_sql),
                params,
            )
            total = int(total_result.scalar_one())
            result = await session.execute(
                text(
                    EVENT_SELECT
                    + where_sql
                    + """
                    ORDER BY e.timestamp_evento DESC NULLS LAST, e.id DESC
                    LIMIT :limit OFFSET :offset
                    """
                ),
                {**params, "limit": page_size, "offset": offset},
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
                text(SESSION_SELECT + " WHERE s.session_key = :session_key"),
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
                    EVENT_SELECT
                    + """
                    WHERE COALESCE(e.sensor, 'unknown') = :sensor
                      AND e.session_id = :session_id
                    ORDER BY e.timestamp_evento, e.id
                    """
                ),
                {
                    "sensor": session_row.sensor,
                    "session_id": session_row.session_id,
                },
            )
            events = tuple(self._event_item(row) for row in events_result)

        score = None
        score_result = await self._get_score(
            session_key=session_key,
            rules_version=rules_version,
        )
        if score_result is not None:
            score = RiskScore(
                score=score_result.score,
                level=score_result.risk_level,
                reasons=tuple(score_result.reasons),
                rules_version=score_result.rules_version,
                calculated_at=score_result.calculated_at,
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

    async def _get_score(self, *, session_key: str, rules_version: str) -> Any:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    SELECT score, risk_level, reasons, rules_version, calculated_at
                    FROM session_risk_scores
                    WHERE session_key = :session_key
                      AND rules_version = :rules_version
                    """
                ),
                {
                    "session_key": session_key,
                    "rules_version": rules_version,
                },
            )
            return result.first()

    async def set_session_review(
        self,
        *,
        session_key: str,
        reviewed: bool,
        actor_id: UUID,
        client_ip: str,
        user_agent: str,
    ) -> SessionListItem | None:
        async with self._session_factory.begin() as session:
            update = await session.execute(
                text(
                    """
                    UPDATE sessions
                    SET reviewed = :reviewed,
                        reviewed_at = CASE WHEN :reviewed THEN NOW() ELSE NULL END,
                        reviewed_by = CASE
                            WHEN :reviewed THEN :actor_id
                            ELSE NULL
                        END,
                        updated_at = NOW()
                    WHERE session_key = :session_key
                    RETURNING session_key
                    """
                ),
                {
                    "session_key": session_key,
                    "reviewed": reviewed,
                    "actor_id": actor_id,
                },
            )
            if update.first() is None:
                return None
            await session.execute(
                text(
                    """
                    INSERT INTO app_audit_log (
                        user_id,
                        action,
                        outcome,
                        client_ip,
                        user_agent,
                        details
                    )
                    VALUES (
                        :user_id,
                        'session.review',
                        'success',
                        :client_ip,
                        :user_agent,
                        CAST(:details AS jsonb)
                    )
                    """
                ),
                {
                    "user_id": actor_id,
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                    "details": json.dumps(
                        {
                            "session_key": session_key,
                            "reviewed": reviewed,
                        },
                        separators=(",", ":"),
                    ),
                },
            )
            result = await session.execute(
                text(
                    SESSION_SELECT
                    + " WHERE s.session_key = :session_key"
                ),
                {
                    "session_key": session_key,
                    "rules_version": "1.0.0",
                },
            )
            return self._session_item(result.one())

    async def start_export(
        self,
        *,
        user_id: UUID,
        resource: str,
        page: int,
        page_size: int,
        filters: dict[str, object],
        encoding: str,
    ) -> UUID:
        async with self._session_factory.begin() as session:
            result = await session.execute(
                text(
                    """
                    INSERT INTO app_export_runs (
                        user_id,
                        resource,
                        status,
                        page,
                        page_size,
                        filters,
                        encoding
                    )
                    VALUES (
                        :user_id,
                        :resource,
                        'running',
                        :page,
                        :page_size,
                        CAST(:filters AS jsonb),
                        :encoding
                    )
                    RETURNING id
                    """
                ),
                {
                    "user_id": user_id,
                    "resource": resource,
                    "page": page,
                    "page_size": page_size,
                    "filters": json.dumps(filters, separators=(",", ":")),
                    "encoding": encoding,
                },
            )
            return result.scalar_one()

    async def complete_export(
        self,
        *,
        export_id: UUID,
        row_count: int,
        total_rows: int,
        filename: str,
    ) -> None:
        async with self._session_factory.begin() as session:
            await session.execute(
                text(
                    """
                    UPDATE app_export_runs
                    SET status = 'completed',
                        row_count = :row_count,
                        total_rows = :total_rows,
                        filename = :filename,
                        finished_at = NOW()
                    WHERE id = :export_id
                    """
                ),
                {
                    "export_id": export_id,
                    "row_count": row_count,
                    "total_rows": total_rows,
                    "filename": filename,
                },
            )

    async def list_alerts(
        self,
        *,
        page: int,
        page_size: int,
        status: str | None = None,
        session_key: str | None = None,
    ) -> Page[AlertItem]:
        offset = (page - 1) * page_size
        clauses: list[str] = []
        params: dict[str, Any] = {}
        if status is not None:
            clauses.append("status = :status")
            params["status"] = status
        if session_key is not None:
            clauses.append("session_key = :session_key")
            params["session_key"] = session_key
        where_sql = " WHERE " + " AND ".join(clauses) if clauses else ""
        async with self._session_factory() as session:
            total_result = await session.execute(
                text("SELECT COUNT(*) FROM alerts" + where_sql),
                params,
            )
            total = int(total_result.scalar_one())
            result = await session.execute(
                text(
                    """
                    SELECT
                        id, session_key, trigger, channel, status,
                        risk_level, risk_score, event_timestamp,
                        triggered_at, sent_at, mttd_seconds,
                        error_code, error_detail
                    FROM alerts
                    """
                    + where_sql
                    + """
                    ORDER BY triggered_at DESC
                    LIMIT :limit OFFSET :offset
                    """
                ),
                {**params, "limit": page_size, "offset": offset},
            )
            items = tuple(
                AlertItem(
                    id=UUID(str(row[0])),
                    session_key=str(row[1]),
                    trigger=str(row[2]),
                    channel=str(row[3]),
                    status=str(row[4]),
                    risk_level=str(row[5]) if row[5] is not None else None,
                    risk_score=int(row[6]) if row[6] is not None else None,
                    event_timestamp=row[7],
                    triggered_at=row[8],
                    sent_at=row[9],
                    mttd_seconds=float(row[10]) if row[10] is not None else None,
                    error_code=str(row[11]) if row[11] is not None else None,
                    error_detail=str(row[12]) if row[12] is not None else None,
                )
                for row in result
            )
        return Page(items=items, page=page, page_size=page_size, total=total)

    async def fail_export(
        self,
        *,
        export_id: UUID,
        error_code: str,
    ) -> None:
        async with self._session_factory.begin() as session:
            await session.execute(
                text(
                    """
                    UPDATE app_export_runs
                    SET status = 'failed',
                        error_code = :error_code,
                        finished_at = NOW()
                    WHERE id = :export_id
                    """
                ),
                {
                    "export_id": export_id,
                    "error_code": error_code[:128],
                },
            )
