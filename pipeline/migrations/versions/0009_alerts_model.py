"""Replace basic alerts table with complete alerts model.

Revision ID: 0009_alerts_model
Revises: 0008_export_runs
Create Date: 2026-06-25
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0009_alerts_model"
down_revision: str | None = "0008_export_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The basic alerts table from 0001 lacks channel, error_detail and proper
    # FK references. Drop it and replace with the complete model. No production
    # data depends on the old table — no pipeline phase has ever written to it.
    op.drop_table("alerts")

    op.create_table(
        "alerts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "session_key",
            sa.Text(),
            sa.ForeignKey("sessions.session_key", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "event_hash",
            sa.Text(),
            sa.ForeignKey("eventos.event_hash", ondelete="SET NULL"),
        ),
        sa.Column(
            "pipeline_run_id",
            sa.Integer(),
            sa.ForeignKey("pipeline_runs.id", ondelete="SET NULL"),
        ),
        sa.Column("trigger", sa.Text(), nullable=False),
        sa.Column(
            "channel",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'telegram'"),
        ),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("risk_level", sa.Text()),
        sa.Column("risk_score", sa.Integer()),
        sa.Column("event_timestamp", sa.DateTime(timezone=True)),
        sa.Column(
            "triggered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("mttd_seconds", sa.Numeric()),
        sa.Column("error_code", sa.Text()),
        sa.Column("error_detail", sa.Text()),
        sa.CheckConstraint(
            "trigger IN ('high_risk', 'successful_login', 'file_download')",
            name="ck_alerts_trigger",
        ),
        sa.CheckConstraint(
            "channel IN ('telegram', 'log', 'webhook')",
            name="ck_alerts_channel",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'failed', 'suppressed')",
            name="ck_alerts_status",
        ),
        sa.CheckConstraint(
            "risk_score IS NULL OR (risk_score >= 0 AND risk_score <= 100)",
            name="ck_alerts_risk_score",
        ),
        sa.UniqueConstraint("session_key", "trigger", name="uq_alerts_session_trigger"),
    )
    with op.get_context().autocommit_block():
        op.create_index(
            "idx_alerts_session_key",
            "alerts",
            ["session_key"],
            postgresql_concurrently=True,
        )
        op.create_index(
            "idx_alerts_status_triggered",
            "alerts",
            ["status", "triggered_at"],
            postgresql_concurrently=True,
        )
        op.create_index(
            "idx_alerts_triggered_at",
            "alerts",
            ["triggered_at"],
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    op.drop_table("alerts")
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_uuid", sa.Text()),
        sa.Column("session_id", sa.Text()),
        sa.Column("event_timestamp", sa.DateTime(timezone=True)),
        sa.Column("processed_timestamp", sa.DateTime(timezone=True)),
        sa.Column(
            "alert_sent_timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
        sa.Column("mttd_seconds", sa.Numeric()),
        sa.Column("alert_type", sa.Text()),
        sa.Column("alert_status", sa.Text()),
        sa.Column("raw_alert", sa.JSON()),
    )
