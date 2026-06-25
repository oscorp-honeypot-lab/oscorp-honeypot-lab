from __future__ import annotations

import unittest
from datetime import datetime, timezone
from uuid import uuid4

from alerts.dispatcher import dispatch_pending_alerts, MAX_ATTEMPTS
from alerts.telegram import TelegramAdapter


BASE_TS = datetime(2026, 6, 25, 21, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

class _FakeCursor:
    def __init__(self, rows: list = None) -> None:
        self.rows = rows or []
        self.executed: list[tuple] = []

    def execute(self, sql: str, params: dict | None = None) -> None:
        self.executed.append((sql, params))

    def fetchall(self) -> list:
        return self.rows

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *args: object) -> None:
        pass


class _FakeConnection:
    def __init__(self, rows: list = None) -> None:
        self._cursor = _FakeCursor(rows)
        self.commits = 0

    def cursor(self) -> _FakeCursor:
        return self._cursor

    def commit(self) -> None:
        self.commits += 1


def _alert_row(
    *,
    status: str = "pending",
    attempt_count: int = 0,
) -> tuple:
    return (
        uuid4(),
        "sensor:abc",
        "high_risk",
        "high",
        75,
        BASE_TS,
        attempt_count,
    )


class _FakeAdapter:
    def __init__(self, *, ok: bool = True, error: str | None = None) -> None:
        self._ok = ok
        self._error = error
        self.calls: list[str] = []

    def send(self, message: str) -> tuple[bool, str | None]:
        self.calls.append(message)
        return self._ok, self._error


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class DispatcherTests(unittest.TestCase):
    def test_returns_zero_when_adapter_is_none(self) -> None:
        conn = _FakeConnection()
        result = dispatch_pending_alerts(conn, None)
        self.assertEqual(result, 0)
        self.assertEqual(conn.commits, 0)

    def test_returns_zero_when_no_pending_alerts(self) -> None:
        conn = _FakeConnection(rows=[])
        adapter = _FakeAdapter(ok=True)
        result = dispatch_pending_alerts(conn, adapter)
        self.assertEqual(result, 0)
        self.assertEqual(adapter.calls, [])

    def test_dispatches_and_marks_sent_on_success(self) -> None:
        conn = _FakeConnection(rows=[_alert_row()])
        adapter = _FakeAdapter(ok=True)
        result = dispatch_pending_alerts(conn, adapter)
        self.assertEqual(result, 1)
        self.assertEqual(len(adapter.calls), 1)
        executed_sqls = [q[0] for q in conn._cursor.executed]
        self.assertTrue(any("sent" in sql.lower() for sql in executed_sqls))

    def test_increments_attempt_count_on_failure(self) -> None:
        conn = _FakeConnection(rows=[_alert_row(attempt_count=0)])
        adapter = _FakeAdapter(ok=False, error="http_429: Too Many Requests")
        result = dispatch_pending_alerts(conn, adapter)
        self.assertEqual(result, 0)
        executed_sqls = [q[0] for q in conn._cursor.executed]
        self.assertTrue(any("attempt_count" in sql for sql in executed_sqls))

    def test_marks_failed_when_max_attempts_reached(self) -> None:
        conn = _FakeConnection(rows=[_alert_row(attempt_count=MAX_ATTEMPTS - 1)])
        adapter = _FakeAdapter(ok=False, error="url_error: timeout")
        dispatch_pending_alerts(conn, adapter)
        sqls = [q[0] for q in conn._cursor.executed]
        self.assertTrue(any("failed" in sql for sql in sqls))

    def test_sends_message_to_each_pending_alert(self) -> None:
        rows = [_alert_row(), _alert_row(attempt_count=1)]
        conn = _FakeConnection(rows=rows)
        adapter = _FakeAdapter(ok=True)
        result = dispatch_pending_alerts(conn, adapter)
        self.assertEqual(result, 2)
        self.assertEqual(len(adapter.calls), 2)

    def test_message_passed_to_adapter_contains_session_key(self) -> None:
        conn = _FakeConnection(rows=[_alert_row()])
        adapter = _FakeAdapter(ok=True)
        dispatch_pending_alerts(conn, adapter)
        self.assertIn("sensor:abc", adapter.calls[0])
