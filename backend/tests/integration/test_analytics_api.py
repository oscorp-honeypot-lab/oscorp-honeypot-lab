from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

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
                """
                DELETE FROM app_export_runs
                WHERE filters ->> 'src_ip' = '203.0.113.18'
                """
            )
            cursor.execute(
                """
                DELETE FROM app_export_runs
                WHERE user_id IN (
                    SELECT id
                    FROM app_users
                    WHERE username LIKE 'test_analytics_%'
                )
                """
            )
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
                        json.dumps(
                            {
                                "password": "must-not-leak",
                                "country": "Argentina",
                            }
                        ),
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
                VALUES (%s, '1.1.0', 75, 'high', CAST(%s AS jsonb))
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


def create_user(role: str) -> tuple[str, str]:
    username = f"test_analytics_{role}_{uuid4().hex[:10]}"
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
                "role": role,
            },
        )
        assert response.status_code == 201
    return username, password


def test_analytics_endpoints_require_authentication() -> None:
    with TestClient(app) as client:
        assert client.get("/api/v1/analytics/summary").status_code == 401
        assert client.get("/api/v1/analytics/timeline").status_code == 401
        assert client.get("/api/v1/sessions").status_code == 401
        assert client.get("/api/v1/events").status_code == 401
        assert client.get("/api/v1/sessions/missing").status_code == 401


def test_viewer_can_read_analytics() -> None:
    username, password = create_user("viewer")
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        assert response.status_code == 200
        assert client.get("/api/v1/analytics/summary").status_code == 200
        assert client.get("/api/v1/analytics/timeline").status_code == 200
        assert client.get("/api/v1/sessions").status_code == 200
        assert client.get("/api/v1/events").status_code == 200


def test_combined_filters(
    analytics_session: dict[str, object],
) -> None:
    with TestClient(app) as client:
        login(client)
        query = (
            "?src_ip=203.0.113.18"
            "&country=argentina"
            "&username=ROOT"
            "&event_type=cowrie.session.file_download"
            "&risk_level=high"
            "&reviewed=false"
            "&from=2026-06-25T17:00:00Z"
            "&to=2026-06-25T19:00:00Z"
        )
        sessions = client.get("/api/v1/sessions" + query)
        assert sessions.status_code == 200
        assert sessions.json()["pagination"]["total"] == 1
        assert sessions.json()["items"][0]["session_key"] == (
            analytics_session["session_key"]
        )
        assert sessions.json()["items"][0]["country"] == "Argentina"

        events = client.get(
            "/api/v1/events"
            "?src_ip=203.0.113.18"
            "&country=argentina"
            "&username=root"
            "&event_type=cowrie.command.input"
        )
        assert events.status_code == 200
        assert events.json()["pagination"]["total"] == 1
        assert events.json()["items"][0]["command"] == "whoami"


def test_session_sorting_and_validation() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get(
            "/api/v1/sessions"
            "?page_size=100&sort_by=event_count&sort_order=asc"
        )
        assert response.status_code == 200
        counts = [item["event_count"] for item in response.json()["items"]]
        assert counts == sorted(counts)

        assert client.get(
            "/api/v1/sessions?sort_by=unsafe"
        ).status_code == 422
        assert client.get(
            "/api/v1/sessions?sort_order=sideways"
        ).status_code == 422


def test_review_transitions_require_analyst(
    analytics_session: dict[str, object],
) -> None:
    viewer_username, viewer_password = create_user("viewer")
    analyst_username, analyst_password = create_user("analyst")

    with TestClient(app) as viewer:
        assert viewer.post(
            "/api/v1/auth/login",
            json={"username": viewer_username, "password": viewer_password},
        ).status_code == 200
        csrf = viewer.cookies.get("oscorp_csrf")
        response = viewer.patch(
            f"/api/v1/sessions/{analytics_session['session_key']}/review",
            headers={"X-CSRF-Token": csrf},
            json={"reviewed": True},
        )
        assert response.status_code == 403

    with TestClient(app) as analyst:
        assert analyst.post(
            "/api/v1/auth/login",
            json={"username": analyst_username, "password": analyst_password},
        ).status_code == 200
        csrf = analyst.cookies.get("oscorp_csrf")
        endpoint = (
            f"/api/v1/sessions/{analytics_session['session_key']}/review"
        )
        reviewed = analyst.patch(
            endpoint,
            headers={"X-CSRF-Token": csrf},
            json={"reviewed": True},
        )
        assert reviewed.status_code == 200
        assert reviewed.json()["reviewed"] is True
        assert reviewed.json()["reviewed_at"] is not None
        assert reviewed.json()["reviewed_by_username"] == analyst_username

        filtered = analyst.get("/api/v1/sessions?reviewed=true")
        assert filtered.status_code == 200
        assert any(
            item["session_key"] == analytics_session["session_key"]
            for item in filtered.json()["items"]
        )

        cleared = analyst.patch(
            endpoint,
            headers={"X-CSRF-Token": csrf},
            json={"reviewed": False},
        )
        assert cleared.status_code == 200
        assert cleared.json()["reviewed"] is False
        assert cleared.json()["reviewed_at"] is None
        assert cleared.json()["reviewed_by"] is None

    with psycopg.connect(database_dsn()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM app_audit_log a
                JOIN app_users u ON u.id = a.user_id
                WHERE u.username = %s
                  AND a.action = 'session.review'
                  AND a.outcome = 'success'
                """,
                (analyst_username,),
            )
            assert cursor.fetchone()[0] == 2


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

        timeline = client.get("/api/v1/analytics/timeline?hours=4")
        assert timeline.status_code == 200
        assert timeline.json()["hours"] == 4
        assert len(timeline.json()["points"]) == 4
        assert client.get(
            "/api/v1/analytics/timeline?hours=721"
        ).status_code == 422

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


def test_csv_exports_content_encoding_and_metadata(
    analytics_session: dict[str, object],
) -> None:
    with TestClient(app) as client:
        login(client)
        sessions = client.get(
            "/api/v1/exports/sessions.csv"
            "?src_ip=203.0.113.18"
            "&country=argentina"
            "&risk_level=high"
            "&page=1"
            "&page_size=1"
        )
        assert sessions.status_code == 200
        assert sessions.content.startswith(b"\xef\xbb\xbf")
        sessions_text = sessions.content.decode("utf-8-sig")
        assert "session_key,session_id,sensor" in sessions_text
        assert str(analytics_session["session_key"]) in sessions_text
        assert "Argentina" in sessions_text
        assert sessions.headers["x-export-row-count"] == "1"
        assert sessions.headers["x-export-page-size"] == "1"
        assert sessions.headers["x-export-encoding"] == "utf-8-sig"
        assert "attachment;" in sessions.headers["content-disposition"]

        events = client.get(
            "/api/v1/exports/events.csv"
            "?src_ip=203.0.113.18"
            "&event_type=cowrie.command.input"
            "&page_size=1"
        )
        assert events.status_code == 200
        assert events.content.startswith(b"\xef\xbb\xbf")
        events_text = events.content.decode("utf-8-sig")
        assert "id,timestamp,event_type" in events_text
        assert "whoami" in events_text
        assert "must-not-leak" not in events_text

        assert client.get(
            "/api/v1/exports/events.csv?page_size=1001"
        ).status_code == 422

        export_ids = (
            sessions.headers["x-export-id"],
            events.headers["x-export-id"],
        )
    with psycopg.connect(database_dsn()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT resource, status, row_count, encoding, filters
                FROM app_export_runs
                WHERE id = ANY(%s::uuid[])
                ORDER BY resource
                """,
                (list(export_ids),),
            )
            rows = cursor.fetchall()
    assert len(rows) == 2
    assert all(row[1] == "completed" for row in rows)
    assert all(row[2] == 1 for row in rows)
    assert all(row[3] == "utf-8-sig" for row in rows)
    assert any(row[4].get("country") == "argentina" for row in rows)


def test_source_mode_field_in_session_response(
    analytics_session: dict[str, object],
) -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/api/v1/sessions?src_ip=203.0.113.18")
        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) >= 1
        target = next(
            item
            for item in items
            if item["session_key"] == analytics_session["session_key"]
        )
        assert target["source_mode"] == "lab"


def test_source_mode_filter_lab_returns_matching_sessions(
    analytics_session: dict[str, object],
) -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get(
            "/api/v1/sessions?source_mode=lab&src_ip=203.0.113.18"
        )
        assert response.status_code == 200
        items = response.json()["items"]
        assert any(
            item["session_key"] == analytics_session["session_key"]
            for item in items
        )
        assert all(item["source_mode"] == "lab" for item in items)


def test_source_mode_filter_real_returns_empty(
    analytics_session: dict[str, object],
) -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get(
            "/api/v1/sessions?source_mode=real&src_ip=203.0.113.18"
        )
        assert response.status_code == 200
        assert response.json()["pagination"]["total"] == 0


def test_source_mode_invalid_value_returns_422() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/api/v1/sessions?source_mode=staging")
        assert response.status_code == 422
