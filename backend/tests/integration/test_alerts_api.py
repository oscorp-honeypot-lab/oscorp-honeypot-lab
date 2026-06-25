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


def test_alerts_endpoint_requires_authentication() -> None:
    with TestClient(app) as client:
        assert client.get("/api/v1/alerts").status_code == 401


def test_alerts_returns_paginated_response_for_authenticated_viewer() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/api/v1/alerts")
        assert response.status_code == 200
        body = response.json()
        assert "items" in body
        assert "pagination" in body
        assert "total" in body["pagination"]
        assert "page" in body["pagination"]
        assert isinstance(body["items"], list)


def test_alerts_pagination_params_are_forwarded() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/api/v1/alerts?page=1&pageSize=5")
        assert response.status_code == 200
        body = response.json()
        assert body["pagination"]["page_size"] == 5


def test_alerts_filter_by_status_returns_200() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/api/v1/alerts?status=pending")
        assert response.status_code == 200
        body = response.json()
        assert all(item["status"] == "pending" for item in body["items"])
