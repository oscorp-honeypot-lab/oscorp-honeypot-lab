"""Create the OSCORP event storage schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-24
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _index_names(table_name: str) -> set[str]:
    return {
        index["name"]
        for index in inspect(op.get_bind()).get_indexes(table_name)
        if index.get("name")
    }


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "eventos" not in tables:
        op.create_table(
            "eventos",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("event_hash", sa.Text(), nullable=False),
            sa.Column("event_uuid", sa.Text()),
            sa.Column("timestamp_evento", sa.DateTime(timezone=True)),
            sa.Column("eventid", sa.Text()),
            sa.Column("session_id", sa.Text()),
            sa.Column("sensor", sa.Text()),
            sa.Column("src_ip", sa.Text()),
            sa.Column("src_port", sa.Integer()),
            sa.Column("username", sa.Text()),
            sa.Column("password", sa.Text()),
            sa.Column("command_input", sa.Text()),
            sa.Column("url", sa.Text()),
            sa.Column("shasum", sa.Text()),
            sa.Column("raw_event", sa.JSON()),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("NOW()"),
            ),
        )
    else:
        columns = {column["name"] for column in inspector.get_columns("eventos")}
        if "event_hash" not in columns:
            op.add_column("eventos", sa.Column("event_hash", sa.Text()))
        if "event_uuid" not in columns:
            op.add_column("eventos", sa.Column("event_uuid", sa.Text()))
        op.execute(
            "ALTER TABLE eventos DROP CONSTRAINT IF EXISTS eventos_event_uuid_key"
        )

    indexes = _index_names("eventos")
    index_specs = (
        ("idx_eventos_event_hash", ["event_hash"], True),
        ("idx_eventos_event_uuid", ["event_uuid"], False),
        ("idx_eventos_eventid", ["eventid"], False),
        ("idx_eventos_session_id", ["session_id"], False),
        ("idx_eventos_src_ip", ["src_ip"], False),
        ("idx_eventos_timestamp", ["timestamp_evento"], False),
    )
    for name, columns, unique in index_specs:
        if name not in indexes:
            op.create_index(name, "eventos", columns, unique=unique)

    tables = set(inspect(op.get_bind()).get_table_names())
    if "pipeline_runs" not in tables:
        op.create_table(
            "pipeline_runs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "started_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("NOW()"),
            ),
            sa.Column("finished_at", sa.DateTime(timezone=True)),
            sa.Column("events_read", sa.Integer(), server_default="0"),
            sa.Column("events_inserted", sa.Integer(), server_default="0"),
            sa.Column("events_indexed", sa.Integer(), server_default="0"),
            sa.Column("alerts_sent", sa.Integer(), server_default="0"),
            sa.Column("errors_count", sa.Integer(), server_default="0"),
            sa.Column("status", sa.Text()),
        )

    if "alerts" not in tables:
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


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_table("pipeline_runs")
    op.drop_table("eventos")
