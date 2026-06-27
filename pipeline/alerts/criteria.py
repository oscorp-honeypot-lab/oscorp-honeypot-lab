from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

ALERT_TRIGGERS = frozenset({"high_risk", "successful_login", "file_download"})

HIGH_RISK_LEVELS = frozenset({"high", "critical"})


@dataclass(frozen=True, slots=True)
class AlertSpec:
    session_key: str
    trigger: str
    channel: str
    status: str
    risk_level: str | None
    risk_score: int | None
    event_timestamp: datetime | None


def evaluate_session_alerts(session: dict) -> tuple[AlertSpec, ...]:
    """Return one AlertSpec per triggered policy for the given session dict."""
    session_key: str = session["session_key"]
    risk_level: str | None = session.get("risk_level")
    risk_score: int | None = session.get("risk_score")
    has_successful_login: bool = bool(session.get("has_successful_login"))
    has_download: bool = bool(session.get("has_download"))
    event_timestamp: datetime | None = session.get("last_event_at")

    specs: list[AlertSpec] = []

    if risk_level in HIGH_RISK_LEVELS:
        specs.append(
            AlertSpec(
                session_key=session_key,
                trigger="high_risk",
                channel="telegram",
                status="pending",
                risk_level=risk_level,
                risk_score=risk_score,
                event_timestamp=event_timestamp,
            )
        )

    if has_successful_login:
        specs.append(
            AlertSpec(
                session_key=session_key,
                trigger="successful_login",
                channel="telegram",
                status="pending",
                risk_level=risk_level,
                risk_score=risk_score,
                event_timestamp=event_timestamp,
            )
        )

    if has_download:
        specs.append(
            AlertSpec(
                session_key=session_key,
                trigger="file_download",
                channel="telegram",
                status="pending",
                risk_level=risk_level,
                risk_score=risk_score,
                event_timestamp=event_timestamp,
            )
        )

    return tuple(specs)
