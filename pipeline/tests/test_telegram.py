from __future__ import annotations

import io
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

    def test_send_uses_telegram_error_description(self) -> None:
        adapter = self._adapter()
        body = b'{"ok":false,"error_code":400,"description":"Bad Request: chat not found"}'
        exc = HTTPError(
            url="url",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=io.BytesIO(body),
        )
        with mock.patch("alerts.telegram.urllib.request.urlopen", side_effect=exc):
            ok, error = adapter.send("test message")
        self.assertFalse(ok)
        self.assertEqual(error, "http_400: Bad Request: chat not found")

    def test_send_returns_false_on_url_error(self) -> None:
        adapter = self._adapter()
        exc = URLError(reason="Connection refused")
        with mock.patch("alerts.telegram.urllib.request.urlopen", side_effect=exc):
            ok, error = adapter.send("test message")
        self.assertFalse(ok)
        self.assertIsNotNone(error)


class FormatAlertMessageTests(unittest.TestCase):
    def _base_msg(self, **overrides) -> str:
        kwargs = dict(
            trigger="high_risk",
            session_key="sensor:abc123",
            risk_level="high",
            risk_score=75,
            event_timestamp="25-06-2026 21:00:00 UTC",
            src_ip="192.168.1.100",
            username="root",
            duration_seconds=30,
            download_count=2,
        )
        kwargs.update(overrides)
        return format_alert_message(**kwargs)

    def test_message_includes_session_key(self) -> None:
        msg = self._base_msg()
        self.assertIn("sensor:abc123", msg)

    def test_high_risk_trigger_has_readable_label(self) -> None:
        msg = self._base_msg(trigger="high_risk")
        self.assertIn("alto riesgo", msg.lower())

    def test_successful_login_trigger_has_readable_label(self) -> None:
        msg = self._base_msg(trigger="successful_login", risk_level=None, risk_score=None)
        self.assertIn("login", msg.lower())

    def test_file_download_trigger_has_readable_label(self) -> None:
        msg = self._base_msg(trigger="file_download", risk_level=None, risk_score=None)
        self.assertIn("descarga", msg.lower())

    def test_critical_risk_emoji_is_included(self) -> None:
        msg = self._base_msg(risk_level="critical", risk_score=90)
        self.assertIn("🔴", msg)

    def test_high_risk_emoji_is_included(self) -> None:
        msg = self._base_msg(risk_level="high", risk_score=75)
        self.assertIn("🟠", msg)

    def test_risk_score_is_included_when_present(self) -> None:
        msg = self._base_msg(risk_score=75)
        self.assertIn("75", msg)

    def test_event_timestamp_is_included_when_present(self) -> None:
        msg = self._base_msg(event_timestamp="25-06-2026 21:00:00 UTC")
        self.assertIn("25-06-2026", msg)

    # --- NEW FORMAT ---

    def test_header_contains_intrusion_alert(self) -> None:
        msg = self._base_msg()
        self.assertIn("🚨", msg)
        self.assertIn("ALERTA DE INTRUSIÓN", msg)

    def test_tipo_label_shown_in_uppercase(self) -> None:
        msg = self._base_msg(trigger="high_risk")
        self.assertIn("ALTO RIESGO", msg)

    def test_tipo_label_for_successful_login_is_uppercase(self) -> None:
        msg = self._base_msg(trigger="successful_login")
        self.assertIn("LOGIN EXITOSO", msg)

    def test_tipo_label_for_file_download_is_uppercase(self) -> None:
        msg = self._base_msg(trigger="file_download")
        self.assertIn("DESCARGA DE ARCHIVO", msg)

    def test_src_ip_is_included_when_present(self) -> None:
        msg = self._base_msg(src_ip="10.0.0.55")
        self.assertIn("10.0.0.55", msg)

    def test_username_is_included_when_present(self) -> None:
        msg = self._base_msg(username="admin")
        self.assertIn("admin", msg)

    def test_duration_is_included_when_present(self) -> None:
        msg = self._base_msg(duration_seconds=120)
        self.assertIn("120", msg)

    def test_download_count_is_included_when_present(self) -> None:
        msg = self._base_msg(download_count=3)
        self.assertIn("📥", msg)
        self.assertIn("3", msg)

    def test_none_optional_fields_show_na(self) -> None:
        msg = self._base_msg(src_ip=None, username=None, duration_seconds=None, download_count=None)
        self.assertEqual(msg.count("N/A"), 4)

    def test_footer_contains_oscorp_signature(self) -> None:
        msg = self._base_msg()
        self.assertIn("🤖 OSCORP ThreatLab", msg)
