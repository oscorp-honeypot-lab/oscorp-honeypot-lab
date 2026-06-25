"""Add attempt_count to alerts for controlled retries.

Revision ID: 0010_alert_attempt_count
Revises: 0009_alerts_model
Create Date: 2026-06-25
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0010_alert_attempt_count"
down_revision: str | None = "0009_alerts_model"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "alerts",
        sa.Column(
            "attempt_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_check_constraint(
        "ck_alerts_attempt_count",
        "alerts",
        "attempt_count >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_alerts_attempt_count", "alerts", type_="check")
    op.drop_column("alerts", "attempt_count")
