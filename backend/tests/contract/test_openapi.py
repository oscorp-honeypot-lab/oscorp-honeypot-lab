from __future__ import annotations

from app.main import app


def test_openapi_exposes_versioned_health_contract() -> None:
    document = app.openapi()
    assert document["info"]["title"] == "OSCORP ThreatLab API"
    assert "/api/v1/health/live" in document["paths"]
    assert "/api/v1/health/ready" in document["paths"]
