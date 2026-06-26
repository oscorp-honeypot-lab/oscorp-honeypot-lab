from __future__ import annotations

from app.main import app


def test_openapi_exposes_versioned_health_contract() -> None:
    document = app.openapi()
    assert document["info"]["title"] == "OSCORP ThreatLab API"
    assert "/api/v1/health/live" in document["paths"]
    assert "/api/v1/health/ready" in document["paths"]
    assert "/api/v1/auth/login" in document["paths"]
    assert "/api/v1/auth/logout" in document["paths"]
    assert "/api/v1/auth/me" in document["paths"]
    assert "/api/v1/users" in document["paths"]
    assert "/api/v1/analytics/summary" in document["paths"]
    assert "/api/v1/analytics/timeline" in document["paths"]
    assert "/api/v1/sessions" in document["paths"]
    assert "/api/v1/events" in document["paths"]
    assert "/api/v1/sessions/{session_key}" in document["paths"]
    assert "/api/v1/sessions/{session_key}/review" in document["paths"]
    assert "/api/v1/exports/sessions.csv" in document["paths"]
    assert "/api/v1/exports/events.csv" in document["paths"]
    assert "/api/v1/reports/latest/{period_type}" in document["paths"]
    assert "/api/v1/reports/latest/{period_type}/download" in document["paths"]
    assert "/api/v1/reports/latest/{period_type}/telegram" in document["paths"]
