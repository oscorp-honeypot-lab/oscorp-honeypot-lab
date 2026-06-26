from __future__ import annotations

import unittest

from vt.adapter import VtResult
from vt.cache import get_cached_vt, store_vt


_SHA = "aabbccdd" * 8

_HIT_ROW = (25, 1, 44, 0, 0, 1719270000, -22, None)

_MALICIOUS_VT = VtResult(
    sha256=_SHA,
    malicious=25,
    suspicious=1,
    undetected=44,
    harmless=0,
    timeout=0,
    last_analysis_date=1719270000,
    reputation=-22,
    error=None,
)

_ERROR_VT = VtResult(
    sha256=_SHA,
    malicious=None,
    suspicious=None,
    undetected=None,
    harmless=None,
    timeout=None,
    last_analysis_date=None,
    reputation=None,
    error="rate_limited",
)


class _FakeCursor:
    def __init__(self, row=None) -> None:
        self._row = row
        self.executed: list[tuple] = []

    def execute(self, sql, params=None): self.executed.append((sql, params))
    def fetchone(self): return self._row
    def __enter__(self): return self
    def __exit__(self, *args): pass


class _FakeConnection:
    def __init__(self, row=None) -> None:
        self._cursor = _FakeCursor(row)
        self.commits = 0

    def cursor(self): return self._cursor
    def commit(self): self.commits += 1


class GetCachedVtTests(unittest.TestCase):
    def test_returns_none_on_cache_miss(self) -> None:
        conn = _FakeConnection(row=None)
        result = get_cached_vt(conn, _SHA)
        self.assertIsNone(result)

    def test_returns_vt_result_on_hit(self) -> None:
        conn = _FakeConnection(row=_HIT_ROW)
        result = get_cached_vt(conn, _SHA)
        self.assertIsNotNone(result)
        self.assertEqual(result.sha256, _SHA)

    def test_hit_includes_malicious_count(self) -> None:
        conn = _FakeConnection(row=_HIT_ROW)
        result = get_cached_vt(conn, _SHA)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.malicious, 25)
        self.assertEqual(result.reputation, -22)


class StoreVtTests(unittest.TestCase):
    def test_store_vt_executes_upsert(self) -> None:
        conn = _FakeConnection()
        store_vt(conn, _MALICIOUS_VT)
        self.assertGreater(len(conn._cursor.executed), 0)

    def test_store_vt_commits(self) -> None:
        conn = _FakeConnection()
        store_vt(conn, _MALICIOUS_VT)
        self.assertEqual(conn.commits, 1)

    def test_store_vt_includes_sha256_in_params(self) -> None:
        conn = _FakeConnection()
        store_vt(conn, _MALICIOUS_VT)
        _, params = conn._cursor.executed[0]
        self.assertEqual(params["sha256"], _SHA)

    def test_store_vt_includes_ttl_in_params(self) -> None:
        conn = _FakeConnection()
        store_vt(conn, _MALICIOUS_VT, ttl_days=15)
        _, params = conn._cursor.executed[0]
        self.assertEqual(params["ttl_days"], 15)
