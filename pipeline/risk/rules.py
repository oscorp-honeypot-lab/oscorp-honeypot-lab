from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class RiskRule:
    rule_id: str
    weight: int
    signal: str
    description: str
    evidence_patterns: tuple[str, ...] = ()
    enabled: bool = True
    reserved_reason: str | None = None

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", self.rule_id):
            raise ValueError(f"Invalid rule_id: {self.rule_id}")
        if self.weight <= 0:
            raise ValueError(f"Rule {self.rule_id} must have a positive weight")
        if self.enabled and self.reserved_reason is not None:
            raise ValueError(
                f"Enabled rule {self.rule_id} cannot have a reserved reason"
            )
        if not self.enabled and not self.reserved_reason:
            raise ValueError(
                f"Disabled rule {self.rule_id} must explain why it is reserved"
            )


@dataclass(frozen=True, slots=True)
class RiskRuleSet:
    version: str
    score_cap: int
    rules: tuple[RiskRule, ...]

    def __post_init__(self) -> None:
        if not re.fullmatch(r"\d+\.\d+\.\d+", self.version):
            raise ValueError(f"Invalid semantic version: {self.version}")
        if self.score_cap != 100:
            raise ValueError("The OSCORP risk score cap must remain 100")
        rule_ids = [rule.rule_id for rule in self.rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("Risk rule identifiers must be unique")

    @property
    def enabled_rules(self) -> tuple[RiskRule, ...]:
        return tuple(rule for rule in self.rules if rule.enabled)

    @property
    def reserved_rules(self) -> tuple[RiskRule, ...]:
        return tuple(rule for rule in self.rules if not rule.enabled)


def level_for_score(score: int) -> RiskLevel:
    if not 0 <= score <= 100:
        raise ValueError("Risk score must be between 0 and 100")
    if score <= 20:
        return RiskLevel.LOW
    if score <= 50:
        return RiskLevel.MEDIUM
    if score <= 80:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


ACTIVE_RULESET = RiskRuleSet(
    version="1.1.0",
    score_cap=100,
    rules=(
        RiskRule(
            rule_id="login_success",
            weight=10,
            signal="session.has_successful_login",
            description="The attacker obtained an interactive login.",
        ),
        RiskRule(
            rule_id="privileged_username",
            weight=5,
            signal="event.username",
            description="A privileged or administrative account was targeted.",
            evidence_patterns=("root", "admin", "administrator", "ubuntu", "oracle"),
        ),
        RiskRule(
            rule_id="reconnaissance",
            weight=10,
            signal="event.command_input",
            description="Commands collected host, identity, process, or network data.",
            evidence_patterns=(
                "whoami",
                "id",
                "uname",
                "hostname",
                "pwd",
                "ls",
                "cat /etc/passwd",
                "ps",
                "netstat",
                "ss",
                "ip addr",
            ),
        ),
        RiskRule(
            rule_id="download_tool",
            weight=15,
            signal="event.command_input",
            description="A command attempted to retrieve a remote payload.",
            evidence_patterns=("wget", "curl", "tftp", "ftp"),
        ),
        RiskRule(
            rule_id="file_download",
            weight=20,
            signal="session.has_download",
            description="Cowrie recorded a completed file download.",
        ),
        RiskRule(
            rule_id="persistence_attempt",
            weight=25,
            signal="event.command_input",
            description="A command attempted to preserve access or autorun a payload.",
            evidence_patterns=(
                "crontab",
                "/etc/cron",
                "systemctl enable",
                "/etc/rc.local",
                "authorized_keys",
                "nohup",
                "screen -dm",
                "tmux new-session",
            ),
        ),
        RiskRule(
            rule_id="malicious_hash_reputation",
            weight=20,
            signal="enrichment.virustotal",
            description="VirusTotal classified a downloaded hash as malicious.",
        ),
        RiskRule(
            rule_id="cloud_origin",
            weight=10,
            signal="enrichment.network_origin",
            description="The source IP belongs to a cloud or hosting provider.",
        ),
    ),
)
