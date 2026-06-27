from __future__ import annotations

import unittest
from datetime import datetime, timezone

from reports.engine import (
    ReportPeriod,
    build_report_dataset,
    closed_report_periods,
    generate_scheduled_reports,
    store_report_run,
)

REFERENCE = datetime(2026, 6, 26, 12, 30, tzinfo=timezone.utc)
DAY_START = datetime(2026, 6, 25, tzinfo=timezone.utc)
DAY_END = datetime(2026, 6, 26, tzinfo=timezone.utc)
WEEK_START = datetime(2026, 6, 15, tzinfo=timezone.utc)
WEEK_END = datetime(2026, 6, 22, tzinfo=timezone.utc)


class _FakeCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, dict | None]] = []
        self._result: list[tuple] = []

    def execute(self, sql: str, params: dict | None = None) -> None:
        self.executed.append((sql, params))
        text = " ".join(sql.split())
        if "COUNT(*)::integer AS event_count" in text:
            self._result = [(42, 7)]
        elif "COUNT(*)::integer AS sessions" in text:
            self._result = [(11, 2, 3)]
        elif "FROM eventos WHERE" in text and "GROUP BY src_ip" in text:
            self._result = [("203.0.113.10", 9)]
        elif "JOIN ip_geo_cache" in text and "GROUP BY g.country" in text:
            self._result = [("Argentina", "AR", 5, 2)]
        elif "GROUP BY COALESCE(username" in text:
            self._result = [("root", "admin", 8)]
        elif "GROUP BY command_input" in text:
            self._result = [("uname -a", 4)]
        elif "AS downloads" in text and "unique_hashes" in text:
            self._result = [(6, 2)]
        elif "GROUP BY url, shasum" in text:
            self._result = [("http://example.test/a.sh", "a" * 64, 3)]
        elif "JOIN vt_hash_cache" in text:
            self._result = [("b" * 64, 12, 1, 2)]
        elif "COUNT(*)::integer FROM sessions" in text:
            self._result = [(1,)]
        elif "SELECT s.session_key" in text:
            self._result = [("sensor:abc", "203.0.113.10", DAY_START, 95)]
        elif "PERCENTILE_CONT" in text:
            self._result = [(30.0, 10.0, 90.0, 85.0, 4, 1, 2)]
        elif "AS total_failed" in text and "affected_sessions" in text:
            self._result = [(1, 1)]
        elif "GROUP BY COALESCE(error_code" in text:
            self._result = [("http_429", 1)]
        else:
            self._result = []

    def fetchone(self) -> tuple:
        return self._result[0]

    def fetchall(self) -> list[tuple]:
        return list(self._result)

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *args: object) -> None:
        pass


class _FakeConnection:
    def __init__(self) -> None:
        self._cursor = _FakeCursor()
        self.commits = 0

    def cursor(self) -> _FakeCursor:
        return self._cursor

    def commit(self) -> None:
        self.commits += 1


class ReportPeriodTests(unittest.TestCase):
    def test_closed_report_periods_returns_previous_day_and_week(self) -> None:
        daily, weekly = closed_report_periods(REFERENCE)
        self.assertEqual(daily.period_type, "daily")
        self.assertEqual(daily.start, DAY_START)
        self.assertEqual(daily.end, DAY_END)
        self.assertEqual(weekly.period_type, "weekly")
        self.assertEqual(weekly.start, WEEK_START)
        self.assertEqual(weekly.end, WEEK_END)


class BuildReportDatasetTests(unittest.TestCase):
    def test_dataset_contains_phase_30_sections(self) -> None:
        conn = _FakeConnection()
        dataset = build_report_dataset(
            conn,
            ReportPeriod("daily", DAY_START, DAY_END),
            generated_at=REFERENCE,
        )
        self.assertEqual(dataset["totals"]["events"], 42)
        self.assertEqual(dataset["totals"]["unique_source_ips"], 7)
        self.assertEqual(dataset["totals"]["sessions"], 11)
        self.assertEqual(dataset["top_countries"][0]["country"], "Argentina")
        self.assertEqual(dataset["top_credentials"][0]["username"], "root")
        self.assertEqual(dataset["top_commands"][0]["command"], "uname -a")
        self.assertEqual(dataset["downloads"]["downloads"], 6)
        self.assertEqual(dataset["malicious_hashes"][0]["malicious"], 12)
        self.assertEqual(dataset["critical_sessions"]["total"], 1)
        self.assertEqual(dataset["mttd"]["failure_rate"], 0.2)
        self.assertEqual(dataset["failed_alerts"]["by_error_code"][0]["error_code"], "http_429")

    def test_queries_use_window_boundaries(self) -> None:
        conn = _FakeConnection()
        build_report_dataset(
            conn,
            ReportPeriod("daily", DAY_START, DAY_END),
            generated_at=REFERENCE,
        )
        params = [params for _, params in conn._cursor.executed if params]
        self.assertTrue(all(item["start"] == DAY_START for item in params if "start" in item))
        self.assertTrue(all(item["end"] == DAY_END for item in params if "end" in item))


class StoreReportRunTests(unittest.TestCase):
    def test_store_report_run_upserts_completed_dataset(self) -> None:
        conn = _FakeConnection()
        store_report_run(
            conn,
            ReportPeriod("daily", DAY_START, DAY_END),
            {"schema_version": "1.0"},
            pipeline_run_id=12,
        )
        sql, params = conn._cursor.executed[-1]
        self.assertIn("ON CONFLICT", sql)
        self.assertEqual(params["period_type"], "daily")
        self.assertEqual(params["pipeline_run_id"], 12)
        self.assertEqual(conn.commits, 1)

    def test_generate_scheduled_reports_stores_daily_and_weekly(self) -> None:
        conn = _FakeConnection()
        periods = generate_scheduled_reports(
            conn,
            reference_at=REFERENCE,
            pipeline_run_id=99,
        )
        self.assertEqual([period.period_type for period in periods], ["daily", "weekly"])
        self.assertEqual(conn.commits, 2)


if __name__ == "__main__":
    unittest.main()
