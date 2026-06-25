from __future__ import annotations

from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from .rules import ACTIVE_RULESET, RiskRuleSet
from .scoring import RiskAssessment, SessionRiskInput, evaluate_session


LOAD_SESSIONS_SQL = """
SELECT
    s.session_key,
    s.has_successful_login,
    s.has_download,
    COALESCE(
        ARRAY_AGG(DISTINCT e.username)
            FILTER (WHERE e.username IS NOT NULL),
        ARRAY[]::text[]
    ) AS usernames,
    COALESCE(
        ARRAY_AGG(e.command_input ORDER BY e.timestamp_evento, e.id)
            FILTER (WHERE e.command_input IS NOT NULL),
        ARRAY[]::text[]
    ) AS commands
FROM sessions s
LEFT JOIN eventos e
  ON s.sensor = COALESCE(e.sensor, 'unknown')
 AND s.session_id = e.session_id
WHERE (%s::text[] IS NULL OR s.session_key = ANY(%s::text[]))
GROUP BY s.session_key, s.has_successful_login, s.has_download
ORDER BY s.session_key
"""


UPSERT_SCORE_SQL = """
INSERT INTO session_risk_scores (
    session_key,
    rules_version,
    score,
    risk_level,
    reasons,
    calculated_at
)
VALUES (%s, %s, %s, %s, %s, NOW())
ON CONFLICT (session_key, rules_version) DO UPDATE
SET
    score = EXCLUDED.score,
    risk_level = EXCLUDED.risk_level,
    reasons = EXCLUDED.reasons,
    calculated_at = NOW()
"""


def load_session_inputs(
    connection: psycopg.Connection[Any],
    session_keys: tuple[str, ...] | None = None,
) -> tuple[SessionRiskInput, ...]:
    keys = list(session_keys) if session_keys is not None else None
    with connection.cursor() as cursor:
        cursor.execute(LOAD_SESSIONS_SQL, (keys, keys))
        rows = cursor.fetchall()
    return tuple(
        SessionRiskInput(
            session_key=str(row[0]),
            has_successful_login=bool(row[1]),
            has_download=bool(row[2]),
            usernames=tuple(row[3]),
            commands=tuple(row[4]),
        )
        for row in rows
    )


def store_assessments(
    connection: psycopg.Connection[Any],
    assessments: tuple[RiskAssessment, ...],
) -> int:
    if not assessments:
        return 0
    with connection.cursor() as cursor:
        cursor.executemany(
            UPSERT_SCORE_SQL,
            [
                (
                    assessment.session_key,
                    assessment.rules_version,
                    assessment.score,
                    assessment.risk_level.value,
                    Jsonb([reason.as_dict() for reason in assessment.reasons]),
                )
                for assessment in assessments
            ],
        )
    connection.commit()
    return len(assessments)


def recalculate_scores(
    connection: psycopg.Connection[Any],
    session_keys: tuple[str, ...] | None = None,
    ruleset: RiskRuleSet = ACTIVE_RULESET,
) -> int:
    assessments = tuple(
        evaluate_session(session, ruleset)
        for session in load_session_inputs(connection, session_keys)
    )
    return store_assessments(connection, assessments)
