from __future__ import annotations

from datetime import datetime, timezone
import os
from uuid import UUID

from fastapi.testclient import TestClient
import psycopg
from psycopg.types.json import Jsonb
import pytest

from app.main import app


REPORT_ID = UUID("31000000-0000-4000-8000-000000000031")


def database_dsn() -> str:
    return os.environ["OSCORP_API_DATABASE_URL"].replace(
        "postgresql+psycopg://",
        "postgresql://",
        1,
    )


def cleanup_report() -> None:
    with psycopg.connect(database_dsn()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM report_deliveries WHERE report_run_id = %s",
                (REPORT_ID,),
            )
            cursor.execute("DELETE FROM report_runs WHERE id = %s", (REPORT_ID,))
            cursor.execute("DELETE FROM app_sessions WHERE client_ip = 'testclient'")


@pytest.fixture(autouse=True)
def isolated_report() -> None:
    cleanup_report()
    dataset = {
        "schema_version": "1.0",
        "totals": {"events": 10, "sessions": 2, "unique_source_ips": 1},
        "top_source_ips": [{"src_ip": "203.0.113.31", "event_count": 10}],
        "top_countries": [],
        "top_credentials": [{"username": "root", "password": "admin", "attempts": 2}],
        "top_commands": [{"command": "uname -a", "executions": 1}],
        "downloads": {"downloads": 1, "unique_hashes": 1, "top_files": []},
        "malicious_hashes": [],
        "critical_sessions": {"total": 0, "top_sessions": []},
        "mttd": {"avg_seconds": 12.5, "total_sent": 1, "total_failed": 0},
        "failed_alerts": {"total_failed": 0, "affected_sessions": 0, "by_error_code": []},
    }
    with psycopg.connect(database_dsn()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO report_runs (
                    id,
                    period_type,
                    period_start,
                    period_end,
                    status,
                    dataset,
                    finished_at
                )
                VALUES (%s, 'daily', %s, %s, 'completed', %s, NOW())
                """,
                (
                    REPORT_ID,
                    datetime(2026, 6, 26, tzinfo=timezone.utc),
                    datetime(2026, 6, 27, tzinfo=timezone.utc),
                    Jsonb(dataset),
                ),
            )
    yield
    cleanup_report()


def login(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": os.environ["OSCORP_API_ADMIN_USERNAME"],
            "password": os.environ["OSCORP_API_ADMIN_PASSWORD"],
        },
    )
    assert response.status_code == 200


def test_latest_report_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/reports/latest/daily")
        assert response.status_code == 401


def test_latest_report_downloads_html_and_csv() -> None:
    with TestClient(app) as client:
        login(client)
        html = client.get("/api/v1/reports/latest/daily/download?format=html")
        assert html.status_code == 200
        assert html.headers["content-type"].startswith("text/html")
        assert "OSCORP ThreatLab" in html.text

        csv_response = client.get("/api/v1/reports/latest/daily/download?format=csv")
        assert csv_response.status_code == 200
        assert csv_response.headers["content-type"].startswith("text/csv")
        assert csv_response.content.startswith(b"\xef\xbb\xbf")

    with psycopg.connect(database_dsn()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM report_deliveries
                WHERE report_run_id = %s
                  AND channel = 'download'
                  AND status = 'completed'
                """,
                (REPORT_ID,),
            )
            assert cursor.fetchone()[0] == 2


def test_telegram_delivery_without_credentials_is_recorded_as_skipped() -> None:
    with TestClient(app) as client:
        login(client)
        client.app.state.report_service._telegram_sender = None
        csrf = client.cookies.get("oscorp_csrf")
        response = client.post(
            "/api/v1/reports/latest/daily/telegram?format=html",
            headers={"X-CSRF-Token": csrf or ""},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "skipped"
        assert body["error_code"] == "telegram_not_configured"

    with psycopg.connect(database_dsn()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT status, error_code
                FROM report_deliveries
                WHERE report_run_id = %s
                  AND channel = 'telegram'
                """,
                (REPORT_ID,),
            )
            assert cursor.fetchone() == ("skipped", "telegram_not_configured")
