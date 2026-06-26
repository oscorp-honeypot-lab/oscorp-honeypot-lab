from __future__ import annotations

import unittest

from vt.adapter import VtResult
from vt.enricher import enrich_download_hashes


_SHA1 = "aabb" * 16
_SHA2 = "ccdd" * 16

_MALICIOUS = VtResult(
    sha256=_SHA1,
    malicious=25, suspicious=1, undetected=44,
    harmless=0, timeout=0,
    last_analysis_date=1719270000, reputation=-22,
    error=None,
)

_RATE_LIMITED = VtResult(
    sha256=_SHA1,
    malicious=None, suspicious=None, undetected=None,
    harmless=None, timeout=None,
    last_analysis_date=None, reputation=None,
    error="rate_limited",
)

_NO_KEY = VtResult(
    sha256=_SHA1,
    malicious=None, suspicious=None, undetected=None,
    harmless=None, timeout=None,
    last_analysis_date=None, reputation=None,
    error="no_api_key",
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
    def __init__(self, result: VtResult | None = None) -> None:
        self._result = result
        self.calls: list[str] = []

    def query(self, sha256: str) -> VtResult:
        self.calls.append(sha256)
        if self._result is not None:
            return VtResult(
                sha256=sha256,
                malicious=self._result.malicious,
                suspicious=self._result.suspicious,
                undetected=self._result.undetected,
                harmless=self._result.harmless,
                timeout=self._result.timeout,
                last_analysis_date=self._result.last_analysis_date,
                reputation=self._result.reputation,
                error=self._result.error,
            )
        return VtResult(
            sha256=sha256, malicious=None, suspicious=None, undetected=None,
            harmless=None, timeout=None, last_analysis_date=None, reputation=None,
            error="api_fail",
        )


class EnricherTests(unittest.TestCase):
    def test_returns_zero_when_no_uncached_hashes(self) -> None:
        conn = _FakeConnection(rows=[])
        adapter = _FakeAdapter()
        result = enrich_download_hashes(conn, adapter)
        self.assertEqual(result, 0)
        self.assertEqual(adapter.calls, [])

    def test_returns_count_of_successfully_enriched(self) -> None:
        conn = _FakeConnection(rows=[(_SHA1,)])
        adapter = _FakeAdapter(_MALICIOUS)
        result = enrich_download_hashes(conn, adapter)
        self.assertEqual(result, 1)

    def test_error_result_is_stored_but_not_counted(self) -> None:
        conn = _FakeConnection(rows=[(_SHA1,)])
        adapter = _FakeAdapter(_RATE_LIMITED)
        result = enrich_download_hashes(conn, adapter)
        self.assertEqual(result, 0)
        self.assertEqual(conn.commits, 1)

    def test_no_api_key_result_is_not_stored(self) -> None:
        conn = _FakeConnection(rows=[(_SHA1,)])
        adapter = _FakeAdapter(_NO_KEY)
        enrich_download_hashes(conn, adapter)
        self.assertEqual(conn.commits, 0)

    def test_stores_result_for_each_hash(self) -> None:
        conn = _FakeConnection(rows=[(_SHA1,), (_SHA2,)])
        adapter = _FakeAdapter(_MALICIOUS)
        enrich_download_hashes(conn, adapter)
        self.assertEqual(len(adapter.calls), 2)
        self.assertEqual(conn.commits, 2)
