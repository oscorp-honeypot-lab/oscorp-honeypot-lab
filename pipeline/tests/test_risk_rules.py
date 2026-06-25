from __future__ import annotations

import unittest

from risk.rules import ACTIVE_RULESET, RiskLevel, RiskRule, level_for_score


class RiskRuleSetTests(unittest.TestCase):
    def test_active_rules_cover_phase_14_signals(self) -> None:
        active_ids = {rule.rule_id for rule in ACTIVE_RULESET.enabled_rules}

        self.assertEqual(
            active_ids,
            {
                "login_success",
                "privileged_username",
                "reconnaissance",
                "download_tool",
                "file_download",
                "persistence_attempt",
            },
        )

    def test_reserved_enrichment_rules_are_disabled(self) -> None:
        reserved_ids = {rule.rule_id for rule in ACTIVE_RULESET.reserved_rules}

        self.assertEqual(
            reserved_ids,
            {"malicious_hash_reputation", "cloud_origin"},
        )
        self.assertTrue(
            all(rule.reserved_reason for rule in ACTIVE_RULESET.reserved_rules)
        )

    def test_active_rules_can_reach_critical_without_reserved_signals(self) -> None:
        maximum_active_score = sum(
            rule.weight for rule in ACTIVE_RULESET.enabled_rules
        )

        self.assertGreaterEqual(maximum_active_score, 81)
        self.assertEqual(
            level_for_score(min(maximum_active_score, ACTIVE_RULESET.score_cap)),
            RiskLevel.CRITICAL,
        )

    def test_level_boundaries(self) -> None:
        expected = {
            0: RiskLevel.LOW,
            20: RiskLevel.LOW,
            21: RiskLevel.MEDIUM,
            50: RiskLevel.MEDIUM,
            51: RiskLevel.HIGH,
            80: RiskLevel.HIGH,
            81: RiskLevel.CRITICAL,
            100: RiskLevel.CRITICAL,
        }

        for score, level in expected.items():
            with self.subTest(score=score):
                self.assertEqual(level_for_score(score), level)

    def test_score_outside_bounds_is_rejected(self) -> None:
        for score in (-1, 101):
            with self.subTest(score=score):
                with self.assertRaises(ValueError):
                    level_for_score(score)

    def test_invalid_rule_definition_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            RiskRule(
                rule_id="Invalid Rule",
                weight=10,
                signal="test",
                description="Invalid identifier.",
            )


if __name__ == "__main__":
    unittest.main()
