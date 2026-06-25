from __future__ import annotations

from dataclasses import dataclass
import re

from .rules import ACTIVE_RULESET, RiskLevel, RiskRuleSet, level_for_score


@dataclass(frozen=True, slots=True)
class SessionRiskInput:
    session_key: str
    has_successful_login: bool
    has_download: bool
    usernames: tuple[str, ...] = ()
    commands: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RiskReason:
    rule_id: str
    weight: int
    evidence: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "weight": self.weight,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    session_key: str
    rules_version: str
    score: int
    risk_level: RiskLevel
    reasons: tuple[RiskReason, ...]


def normalize_text(value: str) -> str:
    return " ".join(value.lower().split())


def command_matches(command: str, pattern: str) -> bool:
    normalized_command = normalize_text(command)
    normalized_pattern = normalize_text(pattern)
    if " " in normalized_pattern or "/" in normalized_pattern:
        return normalized_pattern in normalized_command
    return bool(
        re.search(
            rf"(?:^|[\s;&|()]){re.escape(normalized_pattern)}(?:$|[\s;&|()])",
            normalized_command,
        )
    )


def matching_values(
    values: tuple[str, ...],
    patterns: tuple[str, ...],
) -> tuple[str, ...]:
    matches = {
        value
        for value in values
        if any(command_matches(value, pattern) for pattern in patterns)
    }
    return tuple(sorted(matches)[:5])


def evaluate_session(
    session: SessionRiskInput,
    ruleset: RiskRuleSet = ACTIVE_RULESET,
) -> RiskAssessment:
    reasons: list[RiskReason] = []
    normalized_usernames = {
        normalize_text(username)
        for username in session.usernames
        if username.strip()
    }

    for rule in ruleset.enabled_rules:
        evidence: tuple[str, ...] = ()
        if rule.rule_id == "login_success" and session.has_successful_login:
            evidence = ("cowrie.login.success",)
        elif rule.rule_id == "privileged_username":
            evidence = tuple(
                sorted(normalized_usernames.intersection(rule.evidence_patterns))
            )
        elif rule.rule_id in {
            "reconnaissance",
            "download_tool",
            "persistence_attempt",
        }:
            evidence = matching_values(session.commands, rule.evidence_patterns)
        elif rule.rule_id == "file_download" and session.has_download:
            evidence = ("cowrie.session.file_download",)

        if evidence:
            reasons.append(
                RiskReason(
                    rule_id=rule.rule_id,
                    weight=rule.weight,
                    evidence=evidence,
                )
            )

    score = min(sum(reason.weight for reason in reasons), ruleset.score_cap)
    return RiskAssessment(
        session_key=session.session_key,
        rules_version=ruleset.version,
        score=score,
        risk_level=level_for_score(score),
        reasons=tuple(reasons),
    )
