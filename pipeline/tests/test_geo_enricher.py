from __future__ import annotations

import unittest

from geo.adapter import GeoResult
from geo.enricher import enrich_session_ips

_GERMANY = GeoResult(
    ip="8.8.8.8",
    country="Germany",
    country_code="DE",
    city="Berlin",
    isp="Deutsche Telekom",
    asn="AS3320",
    latitude=52.5244,
    longitude=13.4105,
    error=None,
)

_PRIVATE = GeoResult(
    ip="172.25.0.12",
    country=None, country_code=None, city=None,
    isp=None, asn=None, latitude=None, longitude=None,
    error="private_range",
)


class _FakeCursor:
    def __init__(self, rows: list | None = None) -> None:
        self.rows = rows or []
        self.executed: list[tuple] = []

    def execute(self, sql, params=None): self.executed.append((sql, params))
    def fetchall(self): return self.rows
    def __enter__(self): return self
    def __exit__(self, *args): pass


class _FakeConnection:
    def __init__(self, rows: list | None = None) -> None:
        self._cursor = _FakeCursor(rows)
        self.commits = 0

    def cursor(self): return self._cursor
    def commit(self): self.commits += 1


class _FakeAdapter:
    def __init__(self, results: dict[str, GeoResult] | None = None) -> None:
        self._results = results or {}
        self.calls: list[str] = []

    def query(self, ip: str) -> GeoResult:
        self.calls.append(ip)
        return self._results.get(ip, GeoResult(
            ip=ip, country=None, country_code=None, city=None,
            isp=None, asn=None, latitude=None, longitude=None,
            error="api_fail:not found",
        ))


class EnricherTests(unittest.TestCase):
    def test_returns_zero_when_no_uncached_ips(self) -> None:
        conn = _FakeConnection(rows=[])
        adapter = _FakeAdapter()
        result = enrich_session_ips(conn, adapter)
        self.assertEqual(result, 0)
        self.assertEqual(adapter.calls, [])

    def test_returns_count_of_successfully_enriched_ips(self) -> None:
        conn = _FakeConnection(rows=[("8.8.8.8",)])
        adapter = _FakeAdapter({"8.8.8.8": _GERMANY})
        result = enrich_session_ips(conn, adapter)
        self.assertEqual(result, 1)
        self.assertIn("8.8.8.8", adapter.calls)

    def test_private_ip_is_queried_but_not_counted_as_success(self) -> None:
        conn = _FakeConnection(rows=[("172.25.0.12",)])
        adapter = _FakeAdapter({"172.25.0.12": _PRIVATE})
        result = enrich_session_ips(conn, adapter)
        self.assertEqual(result, 0)
        self.assertIn("172.25.0.12", adapter.calls)

    def test_stores_result_for_each_ip(self) -> None:
        conn = _FakeConnection(rows=[("8.8.8.8",), ("1.1.1.1",)])
        adapter = _FakeAdapter({
            "8.8.8.8": _GERMANY,
            "1.1.1.1": GeoResult(
                ip="1.1.1.1", country="Australia", country_code="AU",
                city="Sydney", isp="APNIC", asn="AS13335",
                latitude=-33.86, longitude=151.21, error=None,
            ),
        })
        enrich_session_ips(conn, adapter)
        self.assertEqual(len(adapter.calls), 2)
        self.assertEqual(conn.commits, 2)

    def test_error_result_is_stored_but_not_counted(self) -> None:
        rate_limited = GeoResult(
            ip="8.8.8.8", country=None, country_code=None, city=None,
            isp=None, asn=None, latitude=None, longitude=None,
            error="rate_limited",
        )
        conn = _FakeConnection(rows=[("8.8.8.8",)])
        adapter = _FakeAdapter({"8.8.8.8": rate_limited})
        result = enrich_session_ips(conn, adapter)
        self.assertEqual(result, 0)
        self.assertEqual(conn.commits, 1)
