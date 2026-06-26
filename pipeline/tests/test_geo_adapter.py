from __future__ import annotations

import json
import unittest
import unittest.mock as mock
from urllib.error import HTTPError, URLError

from geo.adapter import GeoResult, IpApiAdapter


class PrivateIpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = IpApiAdapter()

    def test_rfc1918_10_network_is_private(self) -> None:
        result = self.adapter.query("10.0.0.1")
        self.assertEqual(result.error, "private_range")
        self.assertIsNone(result.country)

    def test_rfc1918_172_network_is_private(self) -> None:
        result = self.adapter.query("172.25.0.12")
        self.assertEqual(result.error, "private_range")

    def test_loopback_is_private(self) -> None:
        result = self.adapter.query("127.0.0.1")
        self.assertEqual(result.error, "private_range")

    def test_rfc1918_192_network_is_private(self) -> None:
        result = self.adapter.query("192.168.1.100")
        self.assertEqual(result.error, "private_range")

    def test_private_result_preserves_ip(self) -> None:
        result = self.adapter.query("10.1.2.3")
        self.assertEqual(result.ip, "10.1.2.3")


class PublicIpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = IpApiAdapter()

    def _mock_response(self, payload: dict) -> mock.MagicMock:
        fake = mock.MagicMock()
        fake.__enter__ = mock.Mock(return_value=fake)
        fake.__exit__ = mock.Mock(return_value=False)
        fake.read.return_value = json.dumps(payload).encode()
        return fake

    def test_successful_query_returns_geo_fields(self) -> None:
        payload = {
            "status": "success",
            "country": "Germany",
            "countryCode": "DE",
            "city": "Berlin",
            "isp": "Deutsche Telekom",
            "as": "AS3320 Deutsche Telekom AG",
            "lat": 52.5244,
            "lon": 13.4105,
        }
        with mock.patch("geo.adapter.urllib.request.urlopen", return_value=self._mock_response(payload)):
            result = self.adapter.query("8.8.8.8")
        self.assertIsNone(result.error)
        self.assertEqual(result.country, "Germany")
        self.assertEqual(result.country_code, "DE")
        self.assertEqual(result.city, "Berlin")
        self.assertAlmostEqual(result.latitude, 52.5244)
        self.assertAlmostEqual(result.longitude, 13.4105)

    def test_api_fail_returns_error(self) -> None:
        payload = {"status": "fail", "message": "private range"}
        with mock.patch("geo.adapter.urllib.request.urlopen", return_value=self._mock_response(payload)):
            result = self.adapter.query("8.8.8.8")
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertIn("api_fail", result.error)

    def test_rate_limit_returns_rate_limited(self) -> None:
        exc = HTTPError(url="url", code=429, msg="Too Many Requests", hdrs={}, fp=None)
        with mock.patch("geo.adapter.urllib.request.urlopen", side_effect=exc):
            result = self.adapter.query("8.8.8.8")
        self.assertEqual(result.error, "rate_limited")
        self.assertIsNone(result.country)

    def test_url_error_returns_url_error(self) -> None:
        exc = URLError(reason="Connection refused")
        with mock.patch("geo.adapter.urllib.request.urlopen", side_effect=exc):
            result = self.adapter.query("8.8.8.8")
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertIn("url_error", result.error)
