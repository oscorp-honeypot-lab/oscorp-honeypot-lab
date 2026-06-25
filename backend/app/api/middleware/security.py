from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.infrastructure.security import secrets_match


class CsrfMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        session_cookie_name: str,
        csrf_cookie_name: str,
    ) -> None:
        super().__init__(app)
        self._session_cookie_name = session_cookie_name
        self._csrf_cookie_name = csrf_cookie_name

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            session_token = request.cookies.get(self._session_cookie_name)
            if session_token:
                cookie_token = request.cookies.get(self._csrf_cookie_name, "")
                header_token = request.headers.get("x-csrf-token", "")
                if not cookie_token or not header_token or not secrets_match(
                    cookie_token,
                    header_token,
                ):
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "csrf_validation_failed"},
                    )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)
        response.headers["content-security-policy"] = (
            "default-src 'none'; "
            "script-src https://cdn.jsdelivr.net; "
            "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'none'"
        )
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["x-frame-options"] = "DENY"
        response.headers["referrer-policy"] = "no-referrer"
        response.headers["permissions-policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        return response
