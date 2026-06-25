from __future__ import annotations

from typing import Any

import psycopg

from .criteria import AlertSpec, evaluate_session_alerts


LOAD_SESSIONS_FOR_ALERTS_SQL = """
SELECT
    s.session_key,
    s.has_successful_login,
    s.has_download,
    s.last_event_at,
    srs.risk_level,
    srs.score AS risk_score
FROM sessions s
LEFT JOIN session_risk_scores srs
    ON s.session_key = srs.session_key
WHERE (%s::text[] IS NULL OR s.session_key = ANY(%s::text[]))
  AND (srs.id IS NOT NULL OR s.has_successful_login OR s.has_download)
ORDER BY s.session_key
"""


INSERT_ALERT_SQL = """
INSERT INTO alerts (
    session_key,
    pipeline_run_id,
    trigger,
    channel,
    status,
    risk_level,
    risk_score,
    event_timestamp
)
VALUES (
    %(session_key)s,
    %(pipeline_run_id)s,
    %(trigger)s,
    %(channel)s,
    %(status)s,
    %(risk_level)s,
    %(risk_score)s,
    %(event_timestamp)s
)
ON CONFLICT (session_key, trigger) DO NOTHING
"""


def generate_session_alerts(
    connection: psycopg.Connection[Any],
    session_keys: tuple[str, ...] | None = None,
    pipeline_run_id: int | None = None,
) -> int:
    """Evaluate alert criteria for sessions and persist new alerts."""
    keys = list(session_keys) if session_keys is not None else None
    with connection.cursor() as cursor:
        cursor.execute(LOAD_SESSIONS_FOR_ALERTS_SQL, (keys, keys))
        rows = cursor.fetchall()

    all_alerts: list[AlertSpec] = []
    for row in rows:
        session_dict = {
            "session_key": str(row[0]),
            "has_successful_login": bool(row[1]),
            "has_download": bool(row[2]),
            "last_event_at": row[3],
            "risk_level": str(row[4]) if row[4] is not None else None,
            "risk_score": int(row[5]) if row[5] is not None else None,
        }
        all_alerts.extend(evaluate_session_alerts(session_dict))

    return persist_alerts(connection, tuple(all_alerts), pipeline_run_id)


def persist_alerts(
    connection: psycopg.Connection[Any],
    alerts: tuple[AlertSpec, ...],
    pipeline_run_id: int | None = None,
) -> int:
    if not alerts:
        return 0
    with connection.cursor() as cursor:
        cursor.executemany(
            INSERT_ALERT_SQL,
            [
                {
                    "session_key": alert.session_key,
                    "pipeline_run_id": pipeline_run_id,
                    "trigger": alert.trigger,
                    "channel": alert.channel,
                    "status": alert.status,
                    "risk_level": alert.risk_level,
                    "risk_score": alert.risk_score,
                    "event_timestamp": alert.event_timestamp,
                }
                for alert in alerts
            ],
        )
    connection.commit()
    return len(alerts)
