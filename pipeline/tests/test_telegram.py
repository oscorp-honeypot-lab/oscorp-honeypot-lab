from __future__ import annotations

import unittest
import unittest.mock as mock
from urllib.error import HTTPError, URLError
from urllib.request import Request

from alerts.telegram import TelegramAdapter, format_alert_message


class TelegramAdapterFromEnvTests(unittest.TestCase):
    def test_returns_none_when_no_env_vars(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=False):
            env = {k: "" for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")}
            with mock.patch.dict("os.environ", env):
                adapter = TelegramAdapter.from_env()
        self.assertIsNone(adapter)

    def test_returns_none_when_only_token_is_set(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "abc123", "TELEGRAM_CHAT_ID": ""},
        ):
            adapter = TelegramAdapter.from_env()
        self.assertIsNone(adapter)

    def test_returns_none_when_only_chat_id_is_set(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": "-100999"},
        ):
            adapter = TelegramAdapter.from_env()
        self.assertIsNone(adapter)

    def test_returns_adapter_when_both_vars_are_set(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "bot:TOKEN", "TELEGRAM_CHAT_ID": "-100999"},
        ):
            adapter = TelegramAdapter.from_env()
        self.assertIsNotNone(adapter)
        assert adapter is not None
        self.assertEqual(adapter.bot_token, "bot:TOKEN")
        self.assertEqual(adapter.chat_id, "-100999")


class TelegramAdapterSendTests(unittest.TestCase):
    def _adapter(self) -> TelegramAdapter:
        return TelegramAdapter(bot_token="fake:TOKEN", chat_id="-100999")

    def test_send_returns_true_on_success(self) -> None:
        adapter = self._adapter()
        fake_response = mock.MagicMock()
        fake_response.status = 200
        with mock.patch("alerts.telegram.urllib.request.urlopen", return_value=fake_response):
            ok, error = adapter.send("test message")
        self.assertTrue(ok)
        self.assertIsNone(error)

    def test_send_returns_false_on_http_error(self) -> None:
        adapter = self._adapter()
        exc = HTTPError(url="url", code=429, msg="Too Many Requests", hdrs={}, fp=None)
        with mock.patch("alerts.telegram.urllib.request.urlopen", side_effect=exc):
            ok, error = adapter.send("test message")
        self.assertFalse(ok)
        self.assertIsNotNone(error)
        assert error is not None
        self.assertIn("429", error)

    def test_send_returns_false_on_url_error(self) -> None:
        adapter = self._adapter()
        exc = URLError(reason="Connection refused")
        with mock.patch("alerts.telegram.urllib.request.urlopen", side_effect=exc):
            ok, error = adapter.send("test message")
        self.assertFalse(ok)
        self.assertIsNotNone(error)


class FormatAlertMessageTests(unittest.TestCase):
    def test_message_includes_session_key(self) -> None:
        msg = format_alert_message(
            trigger="high_risk",
            session_key="sensor:abc123",
            risk_level="high",
            risk_score=75,
            event_timestamp="2026-06-25T21:00:00Z",
        )
        self.assertIn("sensor:abc123", msg)

    def test_high_risk_trigger_has_readable_label(self) -> None:
        msg = format_alert_message(
            trigger="high_risk",
            session_key="s:x",
            risk_level="high",
            risk_score=75,
            event_timestamp=None,
        )
        self.assertIn("alto riesgo", msg.lower())

    def test_successful_login_trigger_has_readable_label(self) -> None:
        msg = format_alert_message(
            trigger="successful_login",
            session_key="s:x",
            risk_level=None,
            risk_score=None,
            event_timestamp=None,
        )
        self.assertIn("login", msg.lower())

    def test_file_download_trigger_has_readable_label(self) -> None:
        msg = format_alert_message(
            trigger="file_download",
            session_key="s:x",
            risk_level=None,
            risk_score=None,
            event_timestamp=None,
        )
        self.assertIn("descarga", msg.lower())

    def test_critical_risk_emoji_is_included(self) -> None:
        msg = format_alert_message(
            trigger="high_risk",
            session_key="s:x",
            risk_level="critical",
            risk_score=90,
            event_timestamp=None,
        )
        self.assertIn("🔴", msg)

    def test_high_risk_emoji_is_included(self) -> None:
        msg = format_alert_message(
            trigger="high_risk",
            session_key="s:x",
            risk_level="high",
            risk_score=75,
            event_timestamp=None,
        )
        self.assertIn("🟠", msg)

    def test_risk_score_is_included_when_present(self) -> None:
        msg = format_alert_message(
            trigger="high_risk",
            session_key="s:x",
            risk_level="high",
            risk_score=75,
            event_timestamp=None,
        )
        self.assertIn("75", msg)

    def test_event_timestamp_is_included_when_present(self) -> None:
        msg = format_alert_message(
            trigger="high_risk",
            session_key="s:x",
            risk_level="high",
            risk_score=75,
            event_timestamp="2026-06-25T21:00:00Z",
        )
        self.assertIn("2026-06-25", msg)
