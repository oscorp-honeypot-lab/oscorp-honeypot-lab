from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from psycopg import Connection
else:
    Connection = Any

try:
    from psycopg.types.json import Jsonb
except ModuleNotFoundError:
    def Jsonb(value: Any) -> Any:
        return value


ReportPeriodType = Literal["daily", "weekly"]
RULES_VERSION = "1.1.0"


@dataclass(frozen=True)
class ReportPeriod:
    period_type: ReportPeriodType
    start: datetime
    end: datetime


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _day_floor(value: datetime) -> datetime:
    value = _utc(value)
    return datetime.combine(value.date(), time.min, tzinfo=timezone.utc)


def _week_floor(value: datetime) -> datetime:
    day_start = _day_floor(value)
    return day_start - timedelta(days=day_start.weekday())


def closed_report_periods(reference_at: datetime) -> tuple[ReportPeriod, ...]:
    day_end = _day_floor(reference_at)
    week_end = _week_floor(reference_at)
    return (
        ReportPeriod("daily", day_end - timedelta(days=1), day_end),
        ReportPeriod("weekly", week_end - timedelta(days=7), week_end),
    )


def _iso(value: datetime | None) -> str | None:
    return _utc(value).isoformat() if value is not None else None


def _num(value: Any) -> float | None:
    return float(value) if value is not None else None


def _event_totals(
    connection: Connection[Any],
    period: ReportPeriod,
) -> dict[str, int]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                COUNT(*)::integer AS event_count,
                (COUNT(DISTINCT src_ip)
                    FILTER (WHERE src_ip IS NOT NULL))::integer AS unique_source_ips
            FROM eventos
            WHERE timestamp_evento >= %(start)s
              AND timestamp_evento < %(end)s
            """,
            {"start": period.start, "end": period.end},
        )
        row = cursor.fetchone()
    return {
        "events": int(row[0]),
        "unique_source_ips": int(row[1]),
    }


def _session_totals(
    connection: Connection[Any],
    period: ReportPeriod,
) -> dict[str, int]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                COUNT(*)::integer AS sessions,
                (COUNT(*) FILTER (WHERE has_successful_login))::integer
                    AS successful_login_sessions,
                (COUNT(*) FILTER (WHERE has_download))::integer
                    AS download_sessions
            FROM sessions
            WHERE first_event_at >= %(start)s
              AND first_event_at < %(end)s
            """,
            {"start": period.start, "end": period.end},
        )
        row = cursor.fetchone()
    return {
        "sessions": int(row[0]),
        "successful_login_sessions": int(row[1]),
        "download_sessions": int(row[2]),
    }


def _top_source_ips(
    connection: Connection[Any],
    period: ReportPeriod,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT src_ip, COUNT(*)::integer AS event_count
            FROM eventos
            WHERE timestamp_evento >= %(start)s
              AND timestamp_evento < %(end)s
              AND src_ip IS NOT NULL
            GROUP BY src_ip
            ORDER BY event_count DESC, src_ip ASC
            LIMIT %(limit)s
            """,
            {"start": period.start, "end": period.end, "limit": limit},
        )
        rows = cursor.fetchall()
    return [
        {"src_ip": str(row[0]), "event_count": int(row[1])}
        for row in rows
    ]


def _top_countries(
    connection: Connection[Any],
    period: ReportPeriod,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                g.country,
                g.country_code,
                COUNT(DISTINCT s.session_key)::integer AS session_count,
                COUNT(DISTINCT s.src_ip)::integer AS unique_ips
            FROM sessions s
            JOIN ip_geo_cache g
              ON g.ip = s.src_ip
             AND g.expires_at > NOW()
            WHERE s.first_event_at >= %(start)s
              AND s.first_event_at < %(end)s
              AND g.error IS NULL
              AND g.country IS NOT NULL
            GROUP BY g.country, g.country_code
            ORDER BY session_count DESC, g.country ASC
            LIMIT %(limit)s
            """,
            {"start": period.start, "end": period.end, "limit": limit},
        )
        rows = cursor.fetchall()
    return [
        {
            "country": str(row[0]),
            "country_code": str(row[1]) if row[1] is not None else None,
            "session_count": int(row[2]),
            "unique_ips": int(row[3]),
        }
        for row in rows
    ]


def _top_credentials(
    connection: Connection[Any],
    period: ReportPeriod,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                COALESCE(username, '') AS username,
                COALESCE(password, '') AS password,
                COUNT(*)::integer AS attempts
            FROM eventos
            WHERE timestamp_evento >= %(start)s
              AND timestamp_evento < %(end)s
              AND eventid IN ('cowrie.login.failed', 'cowrie.login.success')
              AND (username IS NOT NULL OR password IS NOT NULL)
            GROUP BY COALESCE(username, ''), COALESCE(password, '')
            ORDER BY attempts DESC, username ASC, password ASC
            LIMIT %(limit)s
            """,
            {"start": period.start, "end": period.end, "limit": limit},
        )
        rows = cursor.fetchall()
    return [
        {"username": str(row[0]), "password": str(row[1]), "attempts": int(row[2])}
        for row in rows
    ]


def _top_commands(
    connection: Connection[Any],
    period: ReportPeriod,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT command_input, COUNT(*)::integer AS executions
            FROM eventos
            WHERE timestamp_evento >= %(start)s
              AND timestamp_evento < %(end)s
              AND eventid = 'cowrie.command.input'
              AND command_input IS NOT NULL
            GROUP BY command_input
            ORDER BY executions DESC, command_input ASC
            LIMIT %(limit)s
            """,
            {"start": period.start, "end": period.end, "limit": limit},
        )
        rows = cursor.fetchall()
    return [
        {"command": str(row[0]), "executions": int(row[1])}
        for row in rows
    ]


def _download_stats(
    connection: Connection[Any],
    period: ReportPeriod,
    *,
    limit: int,
) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                COUNT(*)::integer AS downloads,
                (COUNT(DISTINCT shasum)
                    FILTER (WHERE shasum IS NOT NULL))::integer AS unique_hashes
            FROM eventos
            WHERE timestamp_evento >= %(start)s
              AND timestamp_evento < %(end)s
              AND eventid = 'cowrie.session.file_download'
            """,
            {"start": period.start, "end": period.end},
        )
        totals = cursor.fetchone()
        cursor.execute(
            """
            SELECT
                url,
                shasum,
                COUNT(*)::integer AS downloads
            FROM eventos
            WHERE timestamp_evento >= %(start)s
              AND timestamp_evento < %(end)s
              AND eventid = 'cowrie.session.file_download'
            GROUP BY url, shasum
            ORDER BY downloads DESC, url ASC NULLS LAST, shasum ASC NULLS LAST
            LIMIT %(limit)s
            """,
            {"start": period.start, "end": period.end, "limit": limit},
        )
        top_rows = cursor.fetchall()
    return {
        "downloads": int(totals[0]),
        "unique_hashes": int(totals[1]),
        "top_files": [
            {
                "url": str(row[0]) if row[0] is not None else None,
                "sha256": str(row[1]) if row[1] is not None else None,
                "downloads": int(row[2]),
            }
            for row in top_rows
        ],
    }


def _malicious_hashes(
    connection: Connection[Any],
    period: ReportPeriod,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                e.shasum,
                MAX(v.malicious)::integer AS malicious,
                MAX(v.suspicious)::integer AS suspicious,
                COUNT(*)::integer AS downloads
            FROM eventos e
            JOIN vt_hash_cache v ON v.sha256 = e.shasum
            WHERE e.timestamp_evento >= %(start)s
              AND e.timestamp_evento < %(end)s
              AND e.eventid = 'cowrie.session.file_download'
              AND v.expires_at > NOW()
              AND v.error IS NULL
              AND v.malicious > 0
            GROUP BY e.shasum
            ORDER BY malicious DESC, downloads DESC, e.shasum ASC
            LIMIT %(limit)s
            """,
            {"start": period.start, "end": period.end, "limit": limit},
        )
        rows = cursor.fetchall()
    return [
        {
            "sha256": str(row[0]),
            "malicious": int(row[1]),
            "suspicious": int(row[2]) if row[2] is not None else None,
            "downloads": int(row[3]),
        }
        for row in rows
    ]


def _critical_sessions(
    connection: Connection[Any],
    period: ReportPeriod,
    *,
    limit: int,
) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*)::integer
            FROM sessions s
            JOIN session_risk_scores r ON r.session_key = s.session_key
            WHERE s.first_event_at >= %(start)s
              AND s.first_event_at < %(end)s
              AND r.rules_version = %(rules_version)s
              AND r.risk_level = 'critical'
            """,
            {
                "start": period.start,
                "end": period.end,
                "rules_version": RULES_VERSION,
            },
        )
        total = int(cursor.fetchone()[0])
        cursor.execute(
            """
            SELECT
                s.session_key,
                s.src_ip,
                s.first_event_at,
                r.score
            FROM sessions s
            JOIN session_risk_scores r ON r.session_key = s.session_key
            WHERE s.first_event_at >= %(start)s
              AND s.first_event_at < %(end)s
              AND r.rules_version = %(rules_version)s
              AND r.risk_level = 'critical'
            ORDER BY r.score DESC, s.first_event_at DESC, s.session_key ASC
            LIMIT %(limit)s
            """,
            {
                "start": period.start,
                "end": period.end,
                "rules_version": RULES_VERSION,
                "limit": limit,
            },
        )
        rows = cursor.fetchall()
    return {
        "total": total,
        "top_sessions": [
            {
                "session_key": str(row[0]),
                "src_ip": str(row[1]) if row[1] is not None else None,
                "first_event_at": _iso(row[2]),
                "risk_score": int(row[3]),
            }
            for row in rows
        ],
    }


def _mttd_stats(
    connection: Connection[Any],
    period: ReportPeriod,
) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                AVG(mttd_seconds) AS avg_seconds,
                MIN(mttd_seconds) AS min_seconds,
                MAX(mttd_seconds) AS max_seconds,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY mttd_seconds)
                    AS p95_seconds,
                (COUNT(*) FILTER (WHERE status = 'sent'))::integer AS total_sent,
                (COUNT(*) FILTER (WHERE status = 'failed'))::integer AS total_failed,
                (COUNT(*) FILTER (WHERE status = 'pending'))::integer AS total_pending
            FROM alerts
            WHERE triggered_at >= %(start)s
              AND triggered_at < %(end)s
            """,
            {"start": period.start, "end": period.end},
        )
        row = cursor.fetchone()
    closed = int(row[4]) + int(row[5])
    return {
        "avg_seconds": _num(row[0]),
        "min_seconds": _num(row[1]),
        "max_seconds": _num(row[2]),
        "p95_seconds": _num(row[3]),
        "total_sent": int(row[4]),
        "total_failed": int(row[5]),
        "total_pending": int(row[6]),
        "failure_rate": round(int(row[5]) / closed, 4) if closed else 0.0,
    }


def _failed_alerts(
    connection: Connection[Any],
    period: ReportPeriod,
) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                COUNT(*)::integer AS total_failed,
                COUNT(DISTINCT session_key)::integer AS affected_sessions
            FROM alerts
            WHERE triggered_at >= %(start)s
              AND triggered_at < %(end)s
              AND status = 'failed'
            """,
            {"start": period.start, "end": period.end},
        )
        totals = cursor.fetchone()
        cursor.execute(
            """
            SELECT
                COALESCE(error_code, 'unknown') AS error_code,
                COUNT(*)::integer AS count
            FROM alerts
            WHERE triggered_at >= %(start)s
              AND triggered_at < %(end)s
              AND status = 'failed'
            GROUP BY COALESCE(error_code, 'unknown')
            ORDER BY count DESC, error_code ASC
            """,
            {"start": period.start, "end": period.end},
        )
        by_error = cursor.fetchall()
    return {
        "total_failed": int(totals[0]),
        "affected_sessions": int(totals[1]),
        "by_error_code": [
            {"error_code": str(row[0]), "count": int(row[1])}
            for row in by_error
        ],
    }


def build_report_dataset(
    connection: Connection[Any],
    period: ReportPeriod,
    *,
    generated_at: datetime | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    generated = _utc(generated_at or datetime.now(timezone.utc))
    dataset: dict[str, Any] = {
        "schema_version": "1.0",
        "period_type": period.period_type,
        "period_start": _iso(period.start),
        "period_end": _iso(period.end),
        "generated_at": _iso(generated),
        "rules_version": RULES_VERSION,
    }
    dataset["totals"] = {
        **_event_totals(connection, period),
        **_session_totals(connection, period),
    }
    dataset["top_source_ips"] = _top_source_ips(connection, period, limit=limit)
    dataset["top_countries"] = _top_countries(connection, period, limit=limit)
    dataset["top_credentials"] = _top_credentials(connection, period, limit=limit)
    dataset["top_commands"] = _top_commands(connection, period, limit=limit)
    dataset["downloads"] = _download_stats(connection, period, limit=limit)
    dataset["malicious_hashes"] = _malicious_hashes(
        connection,
        period,
        limit=limit,
    )
    dataset["critical_sessions"] = _critical_sessions(
        connection,
        period,
        limit=limit,
    )
    dataset["mttd"] = _mttd_stats(connection, period)
    dataset["failed_alerts"] = _failed_alerts(connection, period)
    return dataset


def store_report_run(
    connection: Connection[Any],
    period: ReportPeriod,
    dataset: dict[str, Any],
    *,
    pipeline_run_id: int | None = None,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO report_runs (
                pipeline_run_id,
                period_type,
                period_start,
                period_end,
                status,
                dataset,
                finished_at
            )
            VALUES (
                %(pipeline_run_id)s,
                %(period_type)s,
                %(period_start)s,
                %(period_end)s,
                'completed',
                %(dataset)s,
                NOW()
            )
            ON CONFLICT (period_type, period_start, period_end) DO UPDATE
            SET
                pipeline_run_id = EXCLUDED.pipeline_run_id,
                status = 'completed',
                dataset = EXCLUDED.dataset,
                error_code = NULL,
                error_detail = NULL,
                started_at = NOW(),
                finished_at = NOW()
            """,
            {
                "pipeline_run_id": pipeline_run_id,
                "period_type": period.period_type,
                "period_start": period.start,
                "period_end": period.end,
                "dataset": Jsonb(dataset),
            },
        )
    connection.commit()


def generate_scheduled_reports(
    connection: Connection[Any],
    *,
    reference_at: datetime | None = None,
    pipeline_run_id: int | None = None,
) -> tuple[ReportPeriod, ...]:
    reference = reference_at or datetime.now(timezone.utc)
    periods = closed_report_periods(reference)
    for period in periods:
        dataset = build_report_dataset(
            connection,
            period,
            generated_at=reference,
        )
        store_report_run(connection, period, dataset, pipeline_run_id=pipeline_run_id)
    return periods
