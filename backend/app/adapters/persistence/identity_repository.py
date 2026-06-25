from __future__ import annotations

from datetime import datetime
import json
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.identity import Role, SessionRecord, UserIdentity


class PostgresIdentityRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _user(row: Any) -> UserIdentity:
        return UserIdentity(
            id=row.id,
            username=row.username,
            password_hash=row.password_hash,
            role=Role(row.role),
            is_active=row.is_active,
        )

    async def get_user_by_username(
        self,
        username: str,
    ) -> UserIdentity | None:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    SELECT id, username, password_hash, role, is_active
                    FROM app_users
                    WHERE username = :username
                    """
                ),
                {"username": username},
            )
            row = result.first()
        return self._user(row) if row is not None else None

    async def create_user(
        self,
        *,
        username: str,
        password_hash: str,
        role: Role,
    ) -> UserIdentity:
        try:
            async with self._session_factory.begin() as session:
                result = await session.execute(
                    text(
                        """
                        INSERT INTO app_users (username, password_hash, role)
                        VALUES (:username, :password_hash, :role)
                        RETURNING id, username, password_hash, role, is_active
                        """
                    ),
                    {
                        "username": username,
                        "password_hash": password_hash,
                        "role": role.value,
                    },
                )
                row = result.one()
        except IntegrityError as exc:
            raise ValueError("username_exists") from exc
        return self._user(row)

    async def failed_login_count(
        self,
        *,
        username: str,
        client_ip: str,
        since: datetime,
    ) -> int:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM app_login_attempts
                    WHERE username = :username
                      AND client_ip = :client_ip
                      AND success = FALSE
                      AND created_at >= :since
                    """
                ),
                {
                    "username": username,
                    "client_ip": client_ip,
                    "since": since,
                },
            )
            return int(result.scalar_one())

    async def record_login_attempt(
        self,
        *,
        username: str,
        client_ip: str,
        success: bool,
    ) -> None:
        async with self._session_factory.begin() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO app_login_attempts (
                        username,
                        client_ip,
                        success
                    )
                    VALUES (:username, :client_ip, :success)
                    """
                ),
                {
                    "username": username,
                    "client_ip": client_ip,
                    "success": success,
                },
            )

    async def create_session(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        csrf_token_hash: str,
        idle_expires_at: datetime,
        expires_at: datetime,
        client_ip: str,
        user_agent: str,
    ) -> None:
        async with self._session_factory.begin() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO app_sessions (
                        user_id,
                        token_hash,
                        csrf_token_hash,
                        idle_expires_at,
                        expires_at,
                        client_ip,
                        user_agent
                    )
                    VALUES (
                        :user_id,
                        :token_hash,
                        :csrf_token_hash,
                        :idle_expires_at,
                        :expires_at,
                        :client_ip,
                        :user_agent
                    )
                    """
                ),
                {
                    "user_id": user_id,
                    "token_hash": token_hash,
                    "csrf_token_hash": csrf_token_hash,
                    "idle_expires_at": idle_expires_at,
                    "expires_at": expires_at,
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                },
            )

    async def get_session(self, token_hash: str) -> SessionRecord | None:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    SELECT
                        s.id AS session_id,
                        s.csrf_token_hash,
                        s.idle_expires_at,
                        s.expires_at,
                        s.revoked_at,
                        u.id,
                        u.username,
                        u.password_hash,
                        u.role,
                        u.is_active
                    FROM app_sessions s
                    JOIN app_users u ON u.id = s.user_id
                    WHERE s.token_hash = :token_hash
                    """
                ),
                {"token_hash": token_hash},
            )
            row = result.first()
        if row is None:
            return None
        return SessionRecord(
            id=row.session_id,
            user=self._user(row),
            csrf_token_hash=row.csrf_token_hash,
            idle_expires_at=row.idle_expires_at,
            expires_at=row.expires_at,
            revoked_at=row.revoked_at,
        )

    async def touch_session(
        self,
        *,
        session_id: UUID,
        idle_expires_at: datetime,
    ) -> None:
        async with self._session_factory.begin() as session:
            await session.execute(
                text(
                    """
                    UPDATE app_sessions
                    SET last_seen_at = NOW(),
                        idle_expires_at = :idle_expires_at
                    WHERE id = :session_id
                      AND revoked_at IS NULL
                    """
                ),
                {
                    "session_id": session_id,
                    "idle_expires_at": idle_expires_at,
                },
            )

    async def revoke_session(self, session_id: UUID) -> None:
        async with self._session_factory.begin() as session:
            await session.execute(
                text(
                    """
                    UPDATE app_sessions
                    SET revoked_at = COALESCE(revoked_at, NOW())
                    WHERE id = :session_id
                    """
                ),
                {"session_id": session_id},
            )

    async def write_audit(
        self,
        *,
        user_id: UUID | None,
        action: str,
        outcome: str,
        client_ip: str,
        user_agent: str,
        details: dict[str, object],
    ) -> None:
        async with self._session_factory.begin() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO app_audit_log (
                        user_id,
                        action,
                        outcome,
                        client_ip,
                        user_agent,
                        details
                    )
                    VALUES (
                        :user_id,
                        :action,
                        :outcome,
                        :client_ip,
                        :user_agent,
                        CAST(:details AS jsonb)
                    )
                    """
                ),
                {
                    "user_id": user_id,
                    "action": action,
                    "outcome": outcome,
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                    "details": json.dumps(details, separators=(",", ":")),
                },
            )
