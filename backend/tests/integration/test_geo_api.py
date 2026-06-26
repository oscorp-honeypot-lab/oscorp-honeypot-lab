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


def test_geo_stats_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/analytics/geo-stats")
        assert response.status_code == 401


def test_geo_stats_returns_200_with_expected_structure() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/api/v1/analytics/geo-stats")
        assert response.status_code == 200
        body = response.json()
        assert "total_with_geo" in body
        assert "total_without_geo" in body
        assert "unique_countries" in body
        assert "by_country" in body
        assert isinstance(body["total_with_geo"], int)
        assert isinstance(body["total_without_geo"], int)
        assert isinstance(body["unique_countries"], int)
        assert isinstance(body["by_country"], list)


def test_geo_stats_by_country_items_have_required_fields() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/api/v1/analytics/geo-stats")
        assert response.status_code == 200
        by_country = response.json()["by_country"]
        for item in by_country:
            assert "country" in item
            assert "session_count" in item
            assert "unique_ips" in item
            assert isinstance(item["session_count"], int)
            assert isinstance(item["unique_ips"], int)
