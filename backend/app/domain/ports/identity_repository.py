from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domain.identity import Role, SessionRecord, UserIdentity


class IdentityRepository(Protocol):
    async def get_user_by_username(
        self,
        username: str,
    ) -> UserIdentity | None: ...

    async def create_user(
        self,
        *,
        username: str,
        password_hash: str,
        role: Role,
    ) -> UserIdentity: ...

    async def failed_login_count(
        self,
        *,
        username: str,
        client_ip: str,
        since: datetime,
    ) -> int: ...

    async def record_login_attempt(
        self,
        *,
        username: str,
        client_ip: str,
        success: bool,
    ) -> None: ...

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
    ) -> None: ...

    async def get_session(self, token_hash: str) -> SessionRecord | None: ...

    async def touch_session(
        self,
        *,
        session_id: UUID,
        idle_expires_at: datetime,
    ) -> None: ...

    async def revoke_session(self, session_id: UUID) -> None: ...

    async def write_audit(
        self,
        *,
        user_id: UUID | None,
        action: str,
        outcome: str,
        client_ip: str,
        user_agent: str,
        details: dict[str, object],
    ) -> None: ...
