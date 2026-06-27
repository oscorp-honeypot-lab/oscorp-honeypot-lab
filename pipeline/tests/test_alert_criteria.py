from __future__ import annotations

import unittest
from datetime import datetime, timezone

from alerts.criteria import evaluate_session_alerts

BASE_TS = datetime(2026, 6, 25, 18, 0, tzinfo=timezone.utc)


def _session(
    *,
    session_key: str = "sensor:abc",
    risk_level: str | None = None,
    risk_score: int | None = None,
    has_successful_login: bool = False,
    has_download: bool = False,
    last_event_at: datetime | None = BASE_TS,
) -> dict:
    return {
        "session_key": session_key,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "has_successful_login": has_successful_login,
        "has_download": has_download,
        "last_event_at": last_event_at,
    }


class AlertCriteriaTests(unittest.TestCase):
    def test_high_risk_generates_high_risk_trigger(self) -> None:
        alerts = evaluate_session_alerts(_session(risk_level="high", risk_score=75))
        triggers = {a.trigger for a in alerts}
        self.assertIn("high_risk", triggers)

    def test_critical_risk_generates_high_risk_trigger(self) -> None:
        alerts = evaluate_session_alerts(_session(risk_level="critical", risk_score=90))
        triggers = {a.trigger for a in alerts}
        self.assertIn("high_risk", triggers)

    def test_low_risk_does_not_generate_high_risk_trigger(self) -> None:
        alerts = evaluate_session_alerts(_session(risk_level="low", risk_score=10))
        triggers = {a.trigger for a in alerts}
        self.assertNotIn("high_risk", triggers)

    def test_medium_risk_does_not_generate_high_risk_trigger(self) -> None:
        alerts = evaluate_session_alerts(_session(risk_level="medium", risk_score=35))
        triggers = {a.trigger for a in alerts}
        self.assertNotIn("high_risk", triggers)

    def test_successful_login_generates_trigger(self) -> None:
        alerts = evaluate_session_alerts(_session(has_successful_login=True))
        triggers = {a.trigger for a in alerts}
        self.assertIn("successful_login", triggers)

    def test_file_download_generates_trigger(self) -> None:
        alerts = evaluate_session_alerts(_session(has_download=True))
        triggers = {a.trigger for a in alerts}
        self.assertIn("file_download", triggers)

    def test_no_signals_generates_no_alerts(self) -> None:
        alerts = evaluate_session_alerts(
            _session(risk_level="low", risk_score=5)
        )
        self.assertEqual(alerts, ())

    def test_multiple_signals_generate_multiple_alerts(self) -> None:
        alerts = evaluate_session_alerts(
            _session(
                risk_level="high",
                risk_score=75,
                has_successful_login=True,
                has_download=True,
            )
        )
        triggers = {a.trigger for a in alerts}
        self.assertIn("high_risk", triggers)
        self.assertIn("successful_login", triggers)
        self.assertIn("file_download", triggers)
        self.assertEqual(len(alerts), 3)

    def test_alert_spec_carries_session_context(self) -> None:
        alerts = evaluate_session_alerts(
            _session(
                session_key="sensor:xyz",
                risk_level="high",
                risk_score=60,
                last_event_at=BASE_TS,
            )
        )
        high = next(a for a in alerts if a.trigger == "high_risk")
        self.assertEqual(high.session_key, "sensor:xyz")
        self.assertEqual(high.risk_level, "high")
        self.assertEqual(high.risk_score, 60)
        self.assertEqual(high.event_timestamp, BASE_TS)
        self.assertEqual(high.channel, "telegram")
        self.assertEqual(high.status, "pending")
