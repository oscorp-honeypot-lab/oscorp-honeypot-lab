from __future__ import annotations

import asyncio

from app.adapters.persistence.identity_repository import (
    PostgresIdentityRepository,
)
from app.application.auth_service import AuthService
from app.domain.identity import Role
from app.infrastructure.config import get_settings
from app.infrastructure.database import create_engine, create_session_factory
from app.infrastructure.security import PasswordManager


async def bootstrap() -> int:
    settings = get_settings()
    if not settings.admin_password:
        raise RuntimeError("OSCORP_API_ADMIN_PASSWORD is required")

    engine = create_engine(settings)
    repository = PostgresIdentityRepository(create_session_factory(engine))
    try:
        existing = await repository.get_user_by_username(
            settings.admin_username.lower()
        )
        if existing is not None:
            print("admin_status=existing")
            return 0
        service = AuthService(
            repository,
            PasswordManager(),
            session_absolute_minutes=settings.session_absolute_minutes,
            session_idle_minutes=settings.session_idle_minutes,
            login_window_minutes=settings.login_window_minutes,
            login_max_failures=settings.login_max_failures,
        )
        await service.create_user(
            actor=None,
            username=settings.admin_username,
            password=settings.admin_password,
            role=Role.ADMIN,
            client_ip="bootstrap",
            user_agent="bootstrap",
            action="user.bootstrap_admin",
        )
        print("admin_status=created")
        return 0
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(bootstrap()))
