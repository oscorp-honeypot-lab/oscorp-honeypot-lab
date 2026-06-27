from __future__ import annotations

import unittest
from datetime import datetime, timezone

from geo.adapter import GeoResult
from geo.cache import get_cached_geo, store_geo

BASE_TS = datetime(2026, 6, 25, 21, 0, tzinfo=timezone.utc)

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
    country=None,
    country_code=None,
    city=None,
    isp=None,
    asn=None,
    latitude=None,
    longitude=None,
    error="private_range",
)


class _FakeCursor:
    def __init__(self, row=None) -> None:
        self._row = row
        self.executed: list[tuple] = []

    def execute(self, sql: str, params=None) -> None:
        self.executed.append((sql, params))

    def fetchone(self):
        return self._row

    def __enter__(self): return self
    def __exit__(self, *args): pass


class _FakeConnection:
    def __init__(self, row=None) -> None:
        self._cursor = _FakeCursor(row)
        self.commits = 0

    def cursor(self): return self._cursor
    def commit(self): self.commits += 1


class GetCachedGeoTests(unittest.TestCase):
    def test_returns_none_on_cache_miss(self) -> None:
        conn = _FakeConnection(row=None)
        result = get_cached_geo(conn, "8.8.8.8")
        self.assertIsNone(result)

    def test_returns_geo_result_on_cache_hit(self) -> None:
        row = ("Germany", "DE", "Berlin", "Deutsche Telekom", "AS3320", 52.5244, 13.4105, None)
        conn = _FakeConnection(row=row)
        result = get_cached_geo(conn, "8.8.8.8")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.country, "Germany")
        self.assertEqual(result.ip, "8.8.8.8")
        self.assertIsNone(result.error)

    def test_returns_private_range_result_from_cache(self) -> None:
        row = (None, None, None, None, None, None, None, "private_range")
        conn = _FakeConnection(row=row)
        result = get_cached_geo(conn, "172.25.0.12")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.error, "private_range")
        self.assertIsNone(result.country)


class StoreGeoTests(unittest.TestCase):
    def test_store_geo_executes_upsert(self) -> None:
        conn = _FakeConnection()
        store_geo(conn, _GERMANY)
        sqls = [q[0] for q in conn._cursor.executed]
        self.assertTrue(any("INSERT" in sql.upper() for sql in sqls))
        self.assertTrue(any("ON CONFLICT" in sql.upper() for sql in sqls))

    def test_store_geo_commits(self) -> None:
        conn = _FakeConnection()
        store_geo(conn, _PRIVATE)
        self.assertEqual(conn.commits, 1)

    def test_store_geo_includes_ip_in_params(self) -> None:
        conn = _FakeConnection()
        store_geo(conn, _GERMANY)
        params = conn._cursor.executed[0][1]
        self.assertEqual(params["ip"], "8.8.8.8")

    def test_store_geo_includes_ttl_in_params(self) -> None:
        conn = _FakeConnection()
        store_geo(conn, _GERMANY, ttl_days=14)
        params = conn._cursor.executed[0][1]
        self.assertEqual(params["ttl_days"], 14)
