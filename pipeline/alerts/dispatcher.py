from __future__ import annotations

from typing import Any

import psycopg

from .telegram import TelegramAdapter, format_alert_message


MAX_ATTEMPTS: int = 3

_LOAD_PENDING_SQL = """
SELECT id, session_key, trigger, risk_level, risk_score, event_timestamp, attempt_count
FROM alerts
WHERE status = 'pending'
  AND channel = 'telegram'
  AND attempt_count < %(max_attempts)s
ORDER BY triggered_at
LIMIT 50
"""

_MARK_SENT_SQL = """
UPDATE alerts
SET status      = 'sent',
    sent_at     = NOW(),
    mttd_seconds = EXTRACT(EPOCH FROM (NOW() - event_timestamp))
WHERE id = %(id)s
"""

_MARK_ATTEMPT_FAILED_SQL = """
UPDATE alerts
SET attempt_count = attempt_count + 1,
    error_code    = %(error_code)s,
    error_detail  = %(error_detail)s,
    status = CASE
        WHEN attempt_count + 1 >= %(max_attempts)s THEN 'failed'
        ELSE 'pending'
    END
WHERE id = %(id)s
"""


def dispatch_pending_alerts(
    connection: psycopg.Connection[Any],
    adapter: TelegramAdapter | None,
    *,
    max_attempts: int = MAX_ATTEMPTS,
) -> int:
    """Send pending Telegram alerts and update their status. Returns count sent."""
    if adapter is None:
        return 0

    with connection.cursor() as cursor:
        cursor.execute(_LOAD_PENDING_SQL, {"max_attempts": max_attempts})
        rows = cursor.fetchall()

    dispatched = 0
    for row in rows:
        alert_id, session_key, trigger, risk_level, risk_score, event_timestamp, attempt_count = row

        message = format_alert_message(
            trigger=str(trigger),
            session_key=str(session_key),
            risk_level=str(risk_level) if risk_level is not None else None,
            risk_score=int(risk_score) if risk_score is not None else None,
            event_timestamp=str(event_timestamp) if event_timestamp is not None else None,
        )

        ok, error_detail = adapter.send(message)

        with connection.cursor() as cursor:
            if ok:
                cursor.execute(_MARK_SENT_SQL, {"id": alert_id})
                dispatched += 1
            else:
                error_code = (error_detail or "unknown")[:50].split(":")[0]
                cursor.execute(
                    _MARK_ATTEMPT_FAILED_SQL,
                    {
                        "id": alert_id,
                        "error_code": error_code,
                        "error_detail": error_detail,
                        "max_attempts": max_attempts,
                    },
                )
        connection.commit()

    return dispatched
