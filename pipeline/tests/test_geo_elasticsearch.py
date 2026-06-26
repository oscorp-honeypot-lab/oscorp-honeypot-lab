from __future__ import annotations

import unittest

from geo.elasticsearch import build_geo_lookup, geo_location_for_ip


class GeoLocationTests(unittest.TestCase):
    def test_returns_dict_with_lat_lon_when_both_present(self) -> None:
        result = geo_location_for_ip(52.5244, 13.4105)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertAlmostEqual(result["lat"], 52.5244)
        self.assertAlmostEqual(result["lon"], 13.4105)

    def test_returns_none_when_lat_is_none(self) -> None:
        self.assertIsNone(geo_location_for_ip(None, 13.4105))

    def test_returns_none_when_lon_is_none(self) -> None:
        self.assertIsNone(geo_location_for_ip(52.5244, None))

    def test_returns_none_when_both_are_none(self) -> None:
        self.assertIsNone(geo_location_for_ip(None, None))

    def test_values_are_coerced_to_float(self) -> None:
        result = geo_location_for_ip(52, 13)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsInstance(result["lat"], float)
        self.assertIsInstance(result["lon"], float)


class _FakeCursor:
    def __init__(self, rows: list) -> None:
        self._rows = rows
        self.executed: list[tuple] = []

    def execute(self, sql, params=None): self.executed.append((sql, params))
    def fetchall(self): return self._rows
    def __enter__(self): return self
    def __exit__(self, *args): pass


class _FakeConnection:
    def __init__(self, rows: list | None = None) -> None:
        self._cursor = _FakeCursor(rows or [])

    def cursor(self): return self._cursor


class BuildGeoLookupTests(unittest.TestCase):
    def test_returns_empty_dict_when_no_ips(self) -> None:
        conn = _FakeConnection()
        result = build_geo_lookup(conn, set())
        self.assertEqual(result, {})
        self.assertEqual(conn._cursor.executed, [])

    def test_returns_geo_for_matching_ips(self) -> None:
        conn = _FakeConnection(rows=[("8.8.8.8", 37.4056, -122.0775)])
        result = build_geo_lookup(conn, {"8.8.8.8"})
        self.assertIn("8.8.8.8", result)
        self.assertAlmostEqual(result["8.8.8.8"]["lat"], 37.4056)
        self.assertAlmostEqual(result["8.8.8.8"]["lon"], -122.0775)

    def test_skips_rows_with_null_lat_lon(self) -> None:
        conn = _FakeConnection(rows=[("8.8.8.8", None, None)])
        result = build_geo_lookup(conn, {"8.8.8.8"})
        self.assertEqual(result, {})

    def test_returns_multiple_ips(self) -> None:
        conn = _FakeConnection(rows=[
            ("8.8.8.8", 37.4056, -122.0775),
            ("1.1.1.1", -33.86, 151.21),
        ])
        result = build_geo_lookup(conn, {"8.8.8.8", "1.1.1.1"})
        self.assertEqual(len(result), 2)
        self.assertIn("1.1.1.1", result)
