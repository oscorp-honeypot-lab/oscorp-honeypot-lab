from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from app.application.auth_service import (
    AuthenticationRequired,
    AuthService,
    CsrfFailed,
)
from app.application.health_service import HealthService
from app.domain.identity import Role, UserIdentity


def get_health_service(request: Request) -> HealthService:
    return request.app.state.health_service


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def user_agent(request: Request) -> str:
    return request.headers.get("user-agent", "")[:512]


async def get_current_user(
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserIdentity:
    settings = request.app.state.settings
    try:
        user, _ = await service.authenticate(
            session_token=request.cookies.get(settings.session_cookie_name),
            client_ip=client_ip(request),
            user_agent=user_agent(request),
        )
    except AuthenticationRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication_required",
        ) from exc
    return user


def require_role(required: Role) -> Callable[..., UserIdentity]:
    async def dependency(
        user: Annotated[UserIdentity, Depends(get_current_user)],
    ) -> UserIdentity:
        if not user.role.allows(required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="insufficient_permissions",
            )
        return user

    return dependency


async def require_admin_csrf(
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> UserIdentity:
    settings = request.app.state.settings
    try:
        user, _ = await service.authenticate(
            session_token=request.cookies.get(settings.session_cookie_name),
            csrf_token=csrf_token,
            require_csrf=True,
            client_ip=client_ip(request),
            user_agent=user_agent(request),
        )
    except AuthenticationRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication_required",
        ) from exc
    except CsrfFailed as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="csrf_validation_failed",
        ) from exc
    if not user.role.allows(Role.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient_permissions",
        )
    return user
