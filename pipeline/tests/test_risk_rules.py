from __future__ import annotations

import unittest

from risk.rules import ACTIVE_RULESET, RiskLevel, RiskRule, level_for_score


class RiskRuleSetTests(unittest.TestCase):
    def test_active_ruleset_version_is_1_1_0(self) -> None:
        self.assertEqual(ACTIVE_RULESET.version, "1.1.0")

    def test_active_rules_cover_all_signals_including_enrichment(self) -> None:
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
                "malicious_hash_reputation",
                "cloud_origin",
            },
        )

    def test_no_reserved_rules_remain_in_active_ruleset(self) -> None:
        self.assertEqual(ACTIVE_RULESET.reserved_rules, ())

    def test_malicious_hash_reputation_rule_is_enabled(self) -> None:
        rule_ids = {r.rule_id for r in ACTIVE_RULESET.enabled_rules}
        self.assertIn("malicious_hash_reputation", rule_ids)

    def test_cloud_origin_rule_is_enabled(self) -> None:
        rule_ids = {r.rule_id for r in ACTIVE_RULESET.enabled_rules}
        self.assertIn("cloud_origin", rule_ids)

    def test_active_rules_can_reach_critical(self) -> None:
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
