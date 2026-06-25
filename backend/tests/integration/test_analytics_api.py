from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from uuid import uuid4

from fastapi.testclient import TestClient
import psycopg
import pytest

from app.main import app


SENSOR = "test-analytics"


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
                "DELETE FROM eventos WHERE sensor = %s",
                (SENSOR,),
            )
            cursor.execute(
                "DELETE FROM sessions WHERE sensor = %s",
                (SENSOR,),
            )
            cursor.execute(
                "DELETE FROM app_sessions WHERE client_ip = 'testclient'"
            )
            cursor.execute(
                """
                DELETE FROM app_audit_log
                WHERE user_id IN (
                    SELECT id
                    FROM app_users
                    WHERE username LIKE 'test_analytics_%'
                )
                """
            )
            cursor.execute(
                "DELETE FROM app_users WHERE username LIKE 'test_analytics_%'"
            )


@pytest.fixture(autouse=True)
def isolated_analytics_data():
    cleanup_test_data()
    yield
    cleanup_test_data()


@pytest.fixture
def analytics_session() -> dict[str, object]:
    suffix = uuid4().hex
    session_id = f"session-{suffix}"
    session_key = f"{SENSOR}:{session_id}"
    timestamp = datetime(2026, 6, 25, 18, 0, tzinfo=timezone.utc)
    rows = (
        (
            f"hash-connect-{suffix}",
            timestamp,
            "cowrie.session.connect",
            None,
            None,
            None,
        ),
        (
            f"hash-command-{suffix}",
            timestamp,
            "cowrie.command.input",
            "whoami",
            None,
            None,
        ),
        (
            f"hash-download-{suffix}",
            timestamp,
            "cowrie.session.file_download",
            None,
            "http://payload-server:8080/test.sh",
            "abc123",
        ),
    )
    with psycopg.connect(database_dsn()) as connection:
        with connection.cursor() as cursor:
            for event_hash, event_at, event_type, command, url, sha256 in rows:
                cursor.execute(
                    """
                    INSERT INTO eventos (
                        event_hash,
                        timestamp_evento,
                        eventid,
                        session_id,
                        sensor,
                        src_ip,
                        src_port,
                        username,
                        password,
                        command_input,
                        url,
                        shasum,
                        raw_event
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        CAST(%s AS jsonb)
                    )
                    """,
                    (
                        event_hash,
                        event_at,
                        event_type,
                        session_id,
                        SENSOR,
                        "203.0.113.18",
                        45123,
                        "root",
                        "must-not-leak",
                        command,
                        url,
                        sha256,
                        json.dumps({"password": "must-not-leak"}),
                    ),
                )
            cursor.execute(
                """
                INSERT INTO sessions (
                    session_key,
                    session_id,
                    sensor,
                    src_ip,
                    src_port,
                    first_event_at,
                    last_event_at,
                    connected_at,
                    closed_at,
                    duration_seconds,
                    lifecycle_status,
                    event_count,
                    login_success_count,
                    login_failed_count,
                    command_count,
                    command_failed_count,
                    download_count,
                    first_username,
                    last_username,
                    has_successful_login,
                    has_download
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    session_key,
                    session_id,
                    SENSOR,
                    "203.0.113.18",
                    45123,
                    timestamp,
                    timestamp,
                    timestamp,
                    timestamp,
                    12,
                    "complete",
                    3,
                    1,
                    0,
                    1,
                    0,
                    1,
                    "root",
                    "root",
                    True,
                    True,
                ),
            )
            cursor.execute(
                """
                INSERT INTO session_risk_scores (
                    session_key,
                    rules_version,
                    score,
                    risk_level,
                    reasons
                )
                VALUES (%s, '1.0.0', 75, 'high', CAST(%s AS jsonb))
                """,
                (
                    session_key,
                    json.dumps([{"rule_id": "test", "weight": 75}]),
                ),
            )
    return {"session_key": session_key, "event_count": len(rows)}


def login(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": os.environ["OSCORP_API_ADMIN_USERNAME"],
            "password": os.environ["OSCORP_API_ADMIN_PASSWORD"],
        },
    )
    assert response.status_code == 200


def create_viewer() -> tuple[str, str]:
    username = f"test_analytics_{uuid4().hex[:10]}"
    password = "A-secure-test-password-18!"
    with TestClient(app) as client:
        login(client)
        csrf = client.cookies.get("oscorp_csrf")
        response = client.post(
            "/api/v1/users",
            headers={"X-CSRF-Token": csrf},
            json={
                "username": username,
                "password": password,
                "role": "viewer",
            },
        )
        assert response.status_code == 201
    return username, password


def test_analytics_endpoints_require_authentication() -> None:
    with TestClient(app) as client:
        assert client.get("/api/v1/analytics/summary").status_code == 401
        assert client.get("/api/v1/sessions").status_code == 401
        assert client.get("/api/v1/events").status_code == 401
        assert client.get("/api/v1/sessions/missing").status_code == 401


def test_viewer_can_read_analytics() -> None:
    username, password = create_viewer()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        assert response.status_code == 200
        assert client.get("/api/v1/analytics/summary").status_code == 200
        assert client.get("/api/v1/sessions").status_code == 200
        assert client.get("/api/v1/events").status_code == 200


def test_summary_and_paginated_reads(
    analytics_session: dict[str, object],
) -> None:
    with TestClient(app) as client:
        login(client)
        summary = client.get("/api/v1/analytics/summary")
        assert summary.status_code == 200

        with psycopg.connect(database_dsn()) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM eventos),
                        (SELECT COUNT(*) FROM sessions)
                    """
                )
                expected_events, expected_sessions = cursor.fetchone()

        assert summary.json()["events"] == expected_events
        assert summary.json()["sessions"] == expected_sessions

        sessions = client.get("/api/v1/sessions?page=1&page_size=1")
        assert sessions.status_code == 200
        assert len(sessions.json()["items"]) == 1
        assert sessions.json()["pagination"]["page_size"] == 1
        assert sessions.json()["pagination"]["total"] == expected_sessions

        events = client.get("/api/v1/events?page=1&page_size=2")
        assert events.status_code == 200
        assert len(events.json()["items"]) == 2
        assert events.json()["pagination"]["total"] == expected_events
        assert "password" not in events.text
        assert "raw_event" not in events.text

        assert client.get("/api/v1/events?page_size=101").status_code == 422


def test_session_detail_contains_analysis_without_secrets(
    analytics_session: dict[str, object],
) -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get(
            f"/api/v1/sessions/{analytics_session['session_key']}"
        )
        assert response.status_code == 200
        detail = response.json()
        assert detail["session"]["risk_score"] == 75
        assert detail["score"]["level"] == "high"
        assert detail["commands"] == ["whoami"]
        assert detail["downloads"][0]["sha256"] == "abc123"
        assert len(detail["events"]) == analytics_session["event_count"]
        assert "must-not-leak" not in response.text
        assert "password" not in response.text
        assert "raw_event" not in response.text

        missing = client.get("/api/v1/sessions/missing-session")
        assert missing.status_code == 404
        assert missing.json()["detail"] == "session_not_found"
