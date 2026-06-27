"""Add operational review state to correlated sessions.

Revision ID: 0007_session_review
Revises: 0006_identity_security
Create Date: 2026-06-25
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_session_review"
down_revision: str | None = "0006_identity_security"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column(
            "reviewed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "sessions",
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
    )
    op.add_column(
        "sessions",
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True)),
    )
    op.create_foreign_key(
        "fk_sessions_reviewed_by_app_users",
        "sessions",
        "app_users",
        ["reviewed_by"],
        ["id"],
        ondelete="SET NULL",
    )
    with op.get_context().autocommit_block():
        op.create_index(
            "idx_sessions_reviewed_last_event",
            "sessions",
            ["reviewed", "last_event_at"],
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    op.drop_index("idx_sessions_reviewed_last_event", table_name="sessions")
    op.drop_constraint(
        "fk_sessions_reviewed_by_app_users",
        "sessions",
        type_="foreignkey",
    )
    op.drop_column("sessions", "reviewed_by")
    op.drop_column("sessions", "reviewed_at")
    op.drop_column("sessions", "reviewed")
