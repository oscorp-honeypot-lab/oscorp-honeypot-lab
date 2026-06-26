from __future__ import annotations

import os

from fastapi.testclient import TestClient

from app.main import app


def login(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": os.environ["OSCORP_API_ADMIN_USERNAME"],
            "password": os.environ["OSCORP_API_ADMIN_PASSWORD"],
        },
    )
    assert response.status_code == 200


def test_mttd_endpoint_requires_authentication() -> None:
    with TestClient(app) as client:
        assert client.get("/api/v1/analytics/mttd").status_code == 401


def test_mttd_returns_stats_for_authenticated_viewer() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/api/v1/analytics/mttd")
        assert response.status_code == 200
        body = response.json()
        assert "total_sent" in body
        assert "total_failed" in body
        assert "total_pending" in body
        assert "failure_rate" in body
        assert "by_trigger" in body
        assert isinstance(body["by_trigger"], list)


def test_mttd_numeric_fields_are_none_or_float_when_no_sent_alerts() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/api/v1/analytics/mttd")
        assert response.status_code == 200
        body = response.json()
        for field in ("avg_seconds", "min_seconds", "max_seconds", "p95_seconds"):
            assert body[field] is None or isinstance(body[field], (int, float))


def test_mttd_by_trigger_items_have_required_fields() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/api/v1/analytics/mttd")
        assert response.status_code == 200
        for item in response.json()["by_trigger"]:
            assert "trigger" in item
            assert "avg_seconds" in item
            assert "count" in item
