from __future__ import annotations

import json
import unittest
import unittest.mock as mock
from urllib.error import HTTPError, URLError

from vt.adapter import VtResult, VirusTotalAdapter


_GOOD_PAYLOAD = {
    "data": {
        "attributes": {
            "last_analysis_stats": {
                "malicious": 25,
                "suspicious": 1,
                "undetected": 44,
                "harmless": 0,
                "timeout": 0,
            },
            "last_analysis_date": 1719270000,
            "reputation": -22,
        }
    }
}

_SHA = "abc123def456" * 4 + "ab"  # 50 char fake sha256


class NoApiKeyTests(unittest.TestCase):
    def test_no_api_key_returns_error(self) -> None:
        adapter = VirusTotalAdapter(api_key=None)
        result = adapter.query(_SHA)
        self.assertEqual(result.error, "no_api_key")

    def test_no_api_key_preserves_sha256(self) -> None:
        adapter = VirusTotalAdapter(api_key=None)
        result = adapter.query(_SHA)
        self.assertEqual(result.sha256, _SHA)

    def test_no_api_key_returns_none_fields(self) -> None:
        adapter = VirusTotalAdapter(api_key=None)
        result = adapter.query(_SHA)
        self.assertIsNone(result.malicious)
        self.assertIsNone(result.reputation)


class PublicHashTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = VirusTotalAdapter(api_key="fake-key-1234")

    def _mock_response(self, payload: dict) -> mock.MagicMock:
        fake = mock.MagicMock()
        fake.__enter__ = mock.Mock(return_value=fake)
        fake.__exit__ = mock.Mock(return_value=False)
        fake.read.return_value = json.dumps(payload).encode()
        return fake

    def test_successful_query_returns_vt_fields(self) -> None:
        with mock.patch(
            "vt.adapter.urllib.request.urlopen",
            return_value=self._mock_response(_GOOD_PAYLOAD),
        ):
            result = self.adapter.query(_SHA)
        self.assertIsNone(result.error)
        self.assertEqual(result.malicious, 25)
        self.assertEqual(result.suspicious, 1)
        self.assertEqual(result.reputation, -22)
        self.assertEqual(result.last_analysis_date, 1719270000)
        self.assertEqual(result.sha256, _SHA)

    def test_rate_limit_returns_rate_limited(self) -> None:
        exc = HTTPError(url="url", code=429, msg="Too Many Requests", hdrs={}, fp=None)
        with mock.patch("vt.adapter.urllib.request.urlopen", side_effect=exc):
            result = self.adapter.query(_SHA)
        self.assertEqual(result.error, "rate_limited")
        self.assertIsNone(result.malicious)

    def test_not_found_returns_not_found(self) -> None:
        exc = HTTPError(url="url", code=404, msg="Not Found", hdrs={}, fp=None)
        with mock.patch("vt.adapter.urllib.request.urlopen", side_effect=exc):
            result = self.adapter.query(_SHA)
        self.assertEqual(result.error, "not_found")

    def test_url_error_returns_url_error(self) -> None:
        exc = URLError(reason="Connection refused")
        with mock.patch("vt.adapter.urllib.request.urlopen", side_effect=exc):
            result = self.adapter.query(_SHA)
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertIn("url_error", result.error)

    def test_http_error_other_returns_http_error_code(self) -> None:
        exc = HTTPError(url="url", code=503, msg="Service Unavailable", hdrs={}, fp=None)
        with mock.patch("vt.adapter.urllib.request.urlopen", side_effect=exc):
            result = self.adapter.query(_SHA)
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertIn("503", result.error)
