from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.domain.identity import Role, SessionCredentials, UserIdentity
from app.domain.ports.identity_repository import IdentityRepository
from app.infrastructure.security import (
    PasswordManager,
    hash_secret,
    new_secret,
    secrets_match,
)


class AuthenticationFailed(Exception):
    pass


class AuthenticationRequired(Exception):
    pass


class CsrfFailed(Exception):
    pass


class LoginRateLimited(Exception):
    pass


class AuthService:
    def __init__(
        self,
        repository: IdentityRepository,
        password_manager: PasswordManager,
        *,
        session_absolute_minutes: int,
        session_idle_minutes: int,
        login_window_minutes: int,
        login_max_failures: int,
    ) -> None:
        self._repository = repository
        self._password_manager = password_manager
        self._session_absolute = timedelta(minutes=session_absolute_minutes)
        self._session_idle = timedelta(minutes=session_idle_minutes)
        self._login_window = timedelta(minutes=login_window_minutes)
        self._login_max_failures = login_max_failures

    @staticmethod
    def normalize_username(username: str) -> str:
        return username.strip().lower()

    async def login(
        self,
        *,
        username: str,
        password: str,
        client_ip: str,
        user_agent: str,
    ) -> SessionCredentials:
        normalized = self.normalize_username(username)
        now = datetime.now(timezone.utc)
        failures = await self._repository.failed_login_count(
            username=normalized,
            client_ip=client_ip,
            since=now - self._login_window,
        )
        if failures >= self._login_max_failures:
            await self._repository.write_audit(
                user_id=None,
                action="auth.login",
                outcome="rate_limited",
                client_ip=client_ip,
                user_agent=user_agent,
                details={"username": normalized},
            )
            raise LoginRateLimited

        user = await self._repository.get_user_by_username(normalized)
        valid = (
            self._password_manager.verify(
                user.password_hash if user else None,
                password,
            )
            and user is not None
            and user.is_active
        )
        await self._repository.record_login_attempt(
            username=normalized,
            client_ip=client_ip,
            success=valid,
        )
        if not valid or user is None:
            await self._repository.write_audit(
                user_id=user.id if user else None,
                action="auth.login",
                outcome="failed",
                client_ip=client_ip,
                user_agent=user_agent,
                details={"username": normalized},
            )
            raise AuthenticationFailed

        session_token = new_secret()
        csrf_token = new_secret()
        expires_at = now + self._session_absolute
        await self._repository.create_session(
            user_id=user.id,
            token_hash=hash_secret(session_token),
            csrf_token_hash=hash_secret(csrf_token),
            idle_expires_at=min(now + self._session_idle, expires_at),
            expires_at=expires_at,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        await self._repository.write_audit(
            user_id=user.id,
            action="auth.login",
            outcome="success",
            client_ip=client_ip,
            user_agent=user_agent,
            details={},
        )
        return SessionCredentials(
            session_token=session_token,
            csrf_token=csrf_token,
            user=user,
            expires_at=expires_at,
        )

    async def authenticate(
        self,
        *,
        session_token: str | None,
        csrf_token: str | None = None,
        require_csrf: bool = False,
        client_ip: str,
        user_agent: str,
    ) -> tuple[UserIdentity, UUID]:
        if not session_token:
            raise AuthenticationRequired
        session = await self._repository.get_session(hash_secret(session_token))
        if session is None or session.revoked_at is not None or not session.user.is_active:
            raise AuthenticationRequired

        now = datetime.now(timezone.utc)
        if session.expires_at <= now or session.idle_expires_at <= now:
            await self._repository.revoke_session(session.id)
            await self._repository.write_audit(
                user_id=session.user.id,
                action="auth.session_expired",
                outcome="expired",
                client_ip=client_ip,
                user_agent=user_agent,
                details={},
            )
            raise AuthenticationRequired

        if require_csrf:
            if not csrf_token or not secrets_match(
                hash_secret(csrf_token),
                session.csrf_token_hash,
            ):
                raise CsrfFailed

        await self._repository.touch_session(
            session_id=session.id,
            idle_expires_at=min(now + self._session_idle, session.expires_at),
        )
        return session.user, session.id

    async def logout(
        self,
        *,
        session_token: str | None,
        csrf_token: str | None,
        client_ip: str,
        user_agent: str,
    ) -> None:
        user, session_id = await self.authenticate(
            session_token=session_token,
            csrf_token=csrf_token,
            require_csrf=True,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        await self._repository.revoke_session(session_id)
        await self._repository.write_audit(
            user_id=user.id,
            action="auth.logout",
            outcome="success",
            client_ip=client_ip,
            user_agent=user_agent,
            details={},
        )

    async def create_user(
        self,
        *,
        actor: UserIdentity | None,
        username: str,
        password: str,
        role: Role,
        client_ip: str,
        user_agent: str,
        action: str = "user.create",
    ) -> UserIdentity:
        user = await self._repository.create_user(
            username=self.normalize_username(username),
            password_hash=self._password_manager.hash(password),
            role=role,
        )
        await self._repository.write_audit(
            user_id=actor.id if actor else user.id,
            action=action,
            outcome="success",
            client_ip=client_ip,
            user_agent=user_agent,
            details={"created_user_id": str(user.id), "role": role.value},
        )
        return user
