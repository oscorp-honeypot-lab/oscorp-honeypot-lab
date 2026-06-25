from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status

from app.api.dependencies import (
    client_ip,
    get_auth_service,
    get_current_user,
    require_admin_csrf,
    require_role,
    user_agent,
)
from app.api.schemas import (
    LoginRequest,
    LoginResponse,
    UserCreateRequest,
    UserResponse,
)
from app.application.auth_service import (
    AuthenticationFailed,
    AuthenticationRequired,
    AuthService,
    CsrfFailed,
    LoginRateLimited,
)
from app.domain.identity import Role, UserIdentity


router = APIRouter(tags=["identity"])


@router.post("/auth/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginResponse:
    settings = request.app.state.settings
    try:
        credentials = await service.login(
            username=payload.username,
            password=payload.password.get_secret_value(),
            client_ip=client_ip(request),
            user_agent=user_agent(request),
        )
    except AuthenticationFailed as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_credentials",
        ) from exc
    except LoginRateLimited as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="login_rate_limited",
            headers={"Retry-After": str(settings.login_window_minutes * 60)},
        ) from exc

    max_age = settings.session_absolute_minutes * 60
    response.set_cookie(
        settings.session_cookie_name,
        credentials.session_token,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        credentials.csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return LoginResponse(
        user=UserResponse.from_domain(credentials.user),
        expires_at=credentials.expires_at.isoformat(),
    )


@router.get("/auth/me", response_model=UserResponse)
async def me(
    user: Annotated[UserIdentity, Depends(get_current_user)],
) -> UserResponse:
    return UserResponse.from_domain(user)


@router.get("/auth/analyst", response_model=UserResponse)
async def analyst_check(
    user: Annotated[
        UserIdentity,
        Depends(require_role(Role.ANALYST)),
    ],
) -> UserResponse:
    return UserResponse.from_domain(user)


@router.get("/auth/admin", response_model=UserResponse)
async def admin_check(
    user: Annotated[
        UserIdentity,
        Depends(require_role(Role.ADMIN)),
    ],
) -> UserResponse:
    return UserResponse.from_domain(user)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    settings = request.app.state.settings
    try:
        await service.logout(
            session_token=request.cookies.get(settings.session_cookie_name),
            csrf_token=csrf_token,
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
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    payload: UserCreateRequest,
    request: Request,
    actor: Annotated[UserIdentity, Depends(require_admin_csrf)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    try:
        user = await service.create_user(
            actor=actor,
            username=payload.username,
            password=payload.password.get_secret_value(),
            role=payload.role,
            client_ip=client_ip(request),
            user_agent=user_agent(request),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return UserResponse.from_domain(user)
