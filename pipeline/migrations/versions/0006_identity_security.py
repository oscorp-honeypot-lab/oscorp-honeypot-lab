"""Add users, server sessions, login attempts, and audit log.

Revision ID: 0006_identity_security
Revises: 0005_session_risk_scores
Create Date: 2026-06-25
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0006_identity_security"
down_revision: str | None = "0005_session_risk_scores"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
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
        sa.UniqueConstraint("username", name="uq_app_users_username"),
        sa.CheckConstraint(
            "role IN ('viewer', 'analyst', 'admin')",
            name="ck_app_users_role",
        ),
    )

    op.create_table(
        "app_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("idle_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("client_ip", sa.Text()),
        sa.Column("user_agent", sa.Text()),
        sa.UniqueConstraint("token_hash", name="uq_app_sessions_token_hash"),
        sa.CheckConstraint(
            "idle_expires_at <= expires_at",
            name="ck_app_sessions_idle_before_absolute",
        ),
    )

    op.create_table(
        "app_login_attempts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("client_ip", sa.Text(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_table(
        "app_audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app_users.id", ondelete="SET NULL"),
        ),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("client_ip", sa.Text()),
        sa.Column("user_agent", sa.Text()),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    with op.get_context().autocommit_block():
        op.create_index(
            "idx_app_sessions_user_active",
            "app_sessions",
            ["user_id", "expires_at"],
            postgresql_where=sa.text("revoked_at IS NULL"),
            postgresql_concurrently=True,
        )
        op.create_index(
            "idx_app_login_attempts_lookup",
            "app_login_attempts",
            ["username", "client_ip", "created_at"],
            postgresql_concurrently=True,
        )
        op.create_index(
            "idx_app_audit_log_user_created",
            "app_audit_log",
            ["user_id", "created_at"],
            postgresql_concurrently=True,
        )
        op.create_index(
            "idx_app_audit_log_action_created",
            "app_audit_log",
            ["action", "created_at"],
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    op.drop_table("app_audit_log")
    op.drop_table("app_login_attempts")
    op.drop_table("app_sessions")
    op.drop_table("app_users")
