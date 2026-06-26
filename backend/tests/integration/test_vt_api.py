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


def test_vt_stats_requires_authentication() -> None:
    with TestClient(app) as client:
        assert client.get("/api/v1/analytics/vt-stats").status_code == 401


def test_vt_stats_returns_200_for_authenticated_viewer() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/api/v1/analytics/vt-stats")
        assert response.status_code == 200
        body = response.json()
        assert "total_cached" in body
        assert "malicious_detected" in body
        assert "not_found" in body
        assert "error_count" in body
        assert "max_malicious" in body


def test_vt_stats_numeric_fields_are_int_or_none() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/api/v1/analytics/vt-stats")
        assert response.status_code == 200
        body = response.json()
        for field in ("total_cached", "malicious_detected", "not_found", "error_count"):
            assert isinstance(body[field], int)
        assert body["max_malicious"] is None or isinstance(body["max_malicious"], int)
