from __future__ import annotations

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


def cleanup_lab_data() -> None:
    with psycopg.connect(database_dsn()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM lab_runs")
            cursor.execute("DELETE FROM app_sessions WHERE client_ip = 'testclient'")
            cursor.execute(
                "DELETE FROM app_users WHERE username LIKE 'test_lab_%'"
            )


@pytest.fixture(autouse=True)
def isolated_lab_data():
    cleanup_lab_data()
    yield
    cleanup_lab_data()


def admin_login(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": os.environ["OSCORP_API_ADMIN_USERNAME"],
            "password": os.environ["OSCORP_API_ADMIN_PASSWORD"],
        },
    )
    assert response.status_code == 200


def create_viewer_and_login(client: TestClient) -> None:
    admin_login(client)
    csrf = client.cookies.get("oscorp_csrf")
    username = f"test_lab_{uuid4().hex[:10]}"
    password = "A-secure-lab-password-17!"
    resp = client.post(
        "/api/v1/users",
        headers={"X-CSRF-Token": csrf or ""},
        json={"username": username, "password": password, "role": "viewer"},
    )
    assert resp.status_code == 201
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf or ""})
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200


def _noop_background(*_) -> None:
    pass


async def _noop_background_async(run_id: int, scenario: str) -> None:
    pass


def test_post_run_requires_auth() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/lab/run",
            json={"scenario": "brute-force"},
        )
        assert response.status_code == 401


def test_post_run_requires_analyst_role() -> None:
    with TestClient(app) as client:
        create_viewer_and_login(client)
        csrf = client.cookies.get("oscorp_csrf")
        response = client.post(
            "/api/v1/lab/run",
            json={"scenario": "brute-force"},
            headers={"X-CSRF-Token": csrf or ""},
        )
        assert response.status_code == 403


def test_post_run_rejects_invalid_scenario() -> None:
    with TestClient(app) as client:
        admin_login(client)
        csrf = client.cookies.get("oscorp_csrf")
        response = client.post(
            "/api/v1/lab/run",
            json={"scenario": "rm -rf /"},
            headers={"X-CSRF-Token": csrf or ""},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "lab_scenario_invalid"


def test_post_run_returns_202_when_valid() -> None:
    with TestClient(app) as client:
        admin_login(client)
        csrf = client.cookies.get("oscorp_csrf")
        client.app.state.lab_service._run_background = _noop_background_async
        response = client.post(
            "/api/v1/lab/run",
            json={"scenario": "recon"},
            headers={"X-CSRF-Token": csrf or ""},
        )
        assert response.status_code == 202
        body = response.json()
        assert body["scenario"] == "recon"
        assert body["status"] == "queued"
        assert body["actor"] == os.environ["OSCORP_API_ADMIN_USERNAME"]
        assert isinstance(body["id"], int)

    with psycopg.connect(database_dsn()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM lab_runs WHERE scenario = 'recon'")
            assert cursor.fetchone()[0] == 1


def test_get_status_returns_204_when_no_runs() -> None:
    with TestClient(app) as client:
        admin_login(client)
        response = client.get("/api/v1/lab/status")
        assert response.status_code == 204


def test_get_status_returns_run() -> None:
    with psycopg.connect(database_dsn()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO lab_runs (scenario, status, actor)
                VALUES ('full', 'completed', 'admin')
                """
            )

    with TestClient(app) as client:
        admin_login(client)
        response = client.get("/api/v1/lab/status")
        assert response.status_code == 200
        body = response.json()
        assert body["scenario"] == "full"
        assert body["status"] == "completed"
        assert body["actor"] == "admin"


def test_post_run_returns_409_when_run_active() -> None:
    with psycopg.connect(database_dsn()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO lab_runs (scenario, status, actor)
                VALUES ('brute-force', 'running', 'admin')
                """
            )

    with TestClient(app) as client:
        admin_login(client)
        csrf = client.cookies.get("oscorp_csrf")
        response = client.post(
            "/api/v1/lab/run",
            json={"scenario": "recon"},
            headers={"X-CSRF-Token": csrf or ""},
        )
        assert response.status_code == 409
        assert response.json()["detail"] == "lab_run_conflict"


def test_get_logs_returns_text_for_run() -> None:
    run_id: int
    with psycopg.connect(database_dsn()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO lab_runs (scenario, status, actor, log_text)
                VALUES ('full', 'completed', 'admin', '[lab] iniciando escenario full')
                RETURNING id
                """
            )
            run_id = cursor.fetchone()[0]

    with TestClient(app) as client:
        admin_login(client)
        response = client.get(f"/api/v1/lab/logs/{run_id}")
        assert response.status_code == 200
        assert "[lab] iniciando escenario full" in response.text


def test_get_status_requires_auth() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/lab/status")
        assert response.status_code == 401
