"""Create correlated session projections.

Revision ID: 0004_correlated_sessions
Revises: 0003_pipeline_traceability
Create Date: 2026-06-25
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_correlated_sessions"
down_revision: str | None = "0003_pipeline_traceability"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SESSION_SELECT = """
SELECT
    COALESCE(sensor, 'unknown') || ':' || session_id AS session_key,
    session_id,
    COALESCE(sensor, 'unknown') AS sensor,
    (ARRAY_AGG(src_ip ORDER BY timestamp_evento, id)
        FILTER (WHERE src_ip IS NOT NULL))[1] AS src_ip,
    (ARRAY_AGG(src_port ORDER BY timestamp_evento, id)
        FILTER (WHERE src_port IS NOT NULL))[1] AS src_port,
    MIN(timestamp_evento) AS first_event_at,
    MAX(timestamp_evento) AS last_event_at,
    MIN(timestamp_evento) FILTER (
        WHERE eventid = 'cowrie.session.connect'
    ) AS connected_at,
    MAX(timestamp_evento) FILTER (
        WHERE eventid = 'cowrie.session.closed'
    ) AS closed_at,
    CASE
        WHEN COUNT(*) FILTER (
            WHERE eventid = 'cowrie.session.connect'
        ) > 0
        AND COUNT(*) FILTER (
            WHERE eventid = 'cowrie.session.closed'
        ) > 0
        THEN GREATEST(
            EXTRACT(EPOCH FROM (
                MAX(timestamp_evento) FILTER (
                    WHERE eventid = 'cowrie.session.closed'
                )
                - MIN(timestamp_evento) FILTER (
                    WHERE eventid = 'cowrie.session.connect'
                )
            )),
            0
        )
        ELSE NULL
    END AS duration_seconds,
    CASE
        WHEN COUNT(*) FILTER (
            WHERE eventid = 'cowrie.session.connect'
        ) > 0
        AND COUNT(*) FILTER (
            WHERE eventid = 'cowrie.session.closed'
        ) > 0
        THEN 'complete'
        WHEN COUNT(*) FILTER (
            WHERE eventid = 'cowrie.session.connect'
        ) > 0
        THEN 'open'
        ELSE 'incomplete'
    END AS lifecycle_status,
    COUNT(*)::integer AS event_count,
    COUNT(*) FILTER (
        WHERE eventid = 'cowrie.login.success'
    )::integer AS login_success_count,
    COUNT(*) FILTER (
        WHERE eventid = 'cowrie.login.failed'
    )::integer AS login_failed_count,
    COUNT(*) FILTER (
        WHERE eventid = 'cowrie.command.input'
    )::integer AS command_count,
    COUNT(*) FILTER (
        WHERE eventid = 'cowrie.command.failed'
    )::integer AS command_failed_count,
    COUNT(*) FILTER (
        WHERE eventid = 'cowrie.session.file_download'
    )::integer AS download_count,
    (ARRAY_AGG(username ORDER BY timestamp_evento, id)
        FILTER (WHERE username IS NOT NULL))[1] AS first_username,
    (ARRAY_AGG(username ORDER BY timestamp_evento DESC, id DESC)
        FILTER (WHERE username IS NOT NULL))[1] AS last_username,
    BOOL_OR(eventid = 'cowrie.login.success') AS has_successful_login,
    BOOL_OR(eventid = 'cowrie.session.file_download') AS has_download
FROM eventos
WHERE session_id IS NOT NULL
GROUP BY COALESCE(sensor, 'unknown'), session_id
"""


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("session_key", sa.Text(), primary_key=True),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("sensor", sa.Text(), nullable=False),
        sa.Column("src_ip", sa.Text()),
        sa.Column("src_port", sa.Integer()),
        sa.Column("first_event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("duration_seconds", sa.Numeric()),
        sa.Column("lifecycle_status", sa.Text(), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False),
        sa.Column("login_success_count", sa.Integer(), nullable=False),
        sa.Column("login_failed_count", sa.Integer(), nullable=False),
        sa.Column("command_count", sa.Integer(), nullable=False),
        sa.Column("command_failed_count", sa.Integer(), nullable=False),
        sa.Column("download_count", sa.Integer(), nullable=False),
        sa.Column("first_username", sa.Text()),
        sa.Column("last_username", sa.Text()),
        sa.Column("has_successful_login", sa.Boolean(), nullable=False),
        sa.Column("has_download", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "sensor",
            "session_id",
            name="uq_sessions_sensor_session_id",
        ),
        sa.CheckConstraint(
            "lifecycle_status IN ('complete', 'open', 'incomplete')",
            name="ck_sessions_lifecycle_status",
        ),
        sa.CheckConstraint(
            "first_event_at <= last_event_at",
            name="ck_sessions_event_order",
        ),
        sa.CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_sessions_duration",
        ),
        sa.CheckConstraint(
            """
            event_count >= 0
            AND login_success_count >= 0
            AND login_failed_count >= 0
            AND command_count >= 0
            AND command_failed_count >= 0
            AND download_count >= 0
            """,
            name="ck_sessions_nonnegative_counts",
        ),
    )

    op.execute(
        f"""
        INSERT INTO sessions (
            session_key, session_id, sensor, src_ip, src_port,
            first_event_at, last_event_at, connected_at, closed_at,
            duration_seconds, lifecycle_status, event_count,
            login_success_count, login_failed_count, command_count,
            command_failed_count, download_count, first_username,
            last_username, has_successful_login, has_download
        )
        {SESSION_SELECT}
        """
    )

    with op.get_context().autocommit_block():
        op.create_index(
            "idx_sessions_last_event_at",
            "sessions",
            ["last_event_at"],
            postgresql_concurrently=True,
        )
        op.create_index(
            "idx_sessions_src_ip",
            "sessions",
            ["src_ip"],
            postgresql_concurrently=True,
        )
        op.create_index(
            "idx_sessions_lifecycle_status",
            "sessions",
            ["lifecycle_status"],
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    op.drop_table("sessions")
