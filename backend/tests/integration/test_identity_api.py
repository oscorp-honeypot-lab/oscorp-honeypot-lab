from __future__ import annotations

from hashlib import sha256
import os
from uuid import uuid4

from fastapi.testclient import TestClient
import psycopg
import pytest

from app.main import app


def database_dsn() -> str:
    return os.environ["OSCORP_API_DATABASE_URL"].replace(
        "postgresql+psycopg://",
        "postgresql://",
        1,
    )


def cleanup_test_data() -> None:
    with psycopg.connect(database_dsn()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM app_sessions WHERE client_ip = 'testclient'"
            )
            cursor.execute(
                "DELETE FROM app_login_attempts WHERE client_ip = 'testclient'"
            )
            cursor.execute(
                "DELETE FROM app_audit_log WHERE client_ip = 'testclient'"
            )
            cursor.execute(
                "DELETE FROM app_users WHERE username LIKE 'test\\_%' ESCAPE '\\'"
            )


@pytest.fixture(autouse=True)
def isolated_identity_data():
    cleanup_test_data()
    yield
    cleanup_test_data()


def admin_login(client: TestClient):
    return client.post(
        "/api/v1/auth/login",
        json={
            "username": os.environ["OSCORP_API_ADMIN_USERNAME"],
            "password": os.environ["OSCORP_API_ADMIN_PASSWORD"],
        },
    )


def create_user(
    client: TestClient,
    *,
    role: str,
) -> tuple[str, str]:
    username = f"test_{role}_{uuid4().hex[:10]}"
    password = "A-secure-test-password-17!"
    login_response = admin_login(client)
    assert login_response.status_code == 200
    csrf = client.cookies.get("oscorp_csrf")
    response = client.post(
        "/api/v1/users",
        headers={"X-CSRF-Token": csrf},
        json={"username": username, "password": password, "role": role},
    )
    assert response.status_code == 201
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    return username, password


def test_login_authorization_csrf_logout_and_audit() -> None:
    with TestClient(app) as admin_client:
        username, password = create_user(admin_client, role="viewer")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        assert response.status_code == 200
        set_cookie = response.headers["set-cookie"].lower()
        assert "oscorp_session=" in set_cookie
        assert "httponly" in set_cookie
        assert "samesite=lax" in set_cookie
        assert client.get("/api/v1/auth/me").status_code == 200
        assert client.get("/api/v1/auth/analyst").status_code == 403
        assert client.get("/api/v1/auth/admin").status_code == 403

        assert client.post("/api/v1/auth/logout").status_code == 403
        csrf = client.cookies.get("oscorp_csrf")
        assert client.post(
            "/api/v1/auth/logout",
            headers={"X-CSRF-Token": csrf},
        ).status_code == 204
        assert client.get("/api/v1/auth/me").status_code == 401

    with psycopg.connect(database_dsn()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM app_audit_log a
                JOIN app_users u ON u.id = a.user_id
                WHERE u.username = %s
                  AND a.action = 'auth.logout'
                  AND a.outcome = 'success'
                """,
                (username,),
            )
            assert cursor.fetchone()[0] == 1


def test_login_replaces_stale_session_without_csrf_header() -> None:
    with TestClient(app) as client:
        client.cookies.set("oscorp_session", "stale-session")
        client.cookies.set("oscorp_csrf", "stale-csrf")

        response = admin_login(client)

        assert response.status_code == 200
        assert "oscorp_session=" in response.headers["set-cookie"].lower()


def test_analyst_and_admin_permissions() -> None:
    with TestClient(app) as admin_client:
        analyst_username, analyst_password = create_user(
            admin_client,
            role="analyst",
        )
        assert admin_login(admin_client).status_code == 200
        assert admin_client.get("/api/v1/auth/admin").status_code == 200

    with TestClient(app) as analyst_client:
        assert analyst_client.post(
            "/api/v1/auth/login",
            json={
                "username": analyst_username,
                "password": analyst_password,
            },
        ).status_code == 200
        assert analyst_client.get("/api/v1/auth/analyst").status_code == 200
        assert analyst_client.get("/api/v1/auth/admin").status_code == 403


def test_expired_session_is_rejected() -> None:
    with TestClient(app) as admin_client:
        username, password = create_user(admin_client, role="viewer")

    with TestClient(app) as client:
        assert client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        ).status_code == 200
        token = client.cookies.get("oscorp_session")
        token_hash = sha256(token.encode("utf-8")).hexdigest()
        with psycopg.connect(database_dsn()) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE app_sessions
                    SET idle_expires_at = NOW() - INTERVAL '1 minute',
                        expires_at = NOW() - INTERVAL '1 minute'
                    WHERE token_hash = %s
                    """,
                    (token_hash,),
                )
        assert client.get("/api/v1/auth/me").status_code == 401


def test_login_rate_limit() -> None:
    username = f"test_missing_{uuid4().hex[:10]}"
    with TestClient(app) as client:
        for _ in range(5):
            response = client.post(
                "/api/v1/auth/login",
                json={"username": username, "password": "incorrect"},
            )
            assert response.status_code == 401
        response = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": "incorrect"},
        )
        assert response.status_code == 429
        assert response.headers["retry-after"] == "900"


def test_security_headers_and_cors_allowlist() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health/live")
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "frame-ancestors 'none'" in response.headers[
            "content-security-policy"
        ]

        preflight = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert preflight.status_code == 200
        assert preflight.headers["access-control-allow-origin"] == (
            "http://localhost:5173"
        )
