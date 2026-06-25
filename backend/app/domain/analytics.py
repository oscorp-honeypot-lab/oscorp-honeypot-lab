from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Page(Generic[T]):
    items: tuple[T, ...]
    page: int
    page_size: int
    total: int


@dataclass(frozen=True, slots=True)
class AnalyticsSummary:
    events: int
    sessions: int
    unique_source_ips: int
    successful_login_sessions: int
    download_sessions: int
    risk_low: int
    risk_medium: int
    risk_high: int
    risk_critical: int
    latest_event_at: datetime | None


@dataclass(frozen=True, slots=True)
class RiskScore:
    score: int
    level: str
    reasons: tuple[dict[str, object], ...]
    rules_version: str
    calculated_at: datetime


@dataclass(frozen=True, slots=True)
class SessionListItem:
    session_key: str
    session_id: str
    sensor: str
    src_ip: str | None
    src_port: int | None
    first_event_at: datetime
    last_event_at: datetime
    duration_seconds: float | None
    lifecycle_status: str
    event_count: int
    command_count: int
    download_count: int
    username: str | None
    has_successful_login: bool
    risk_score: int | None
    risk_level: str | None


@dataclass(frozen=True, slots=True)
class EventListItem:
    id: int
    timestamp: datetime | None
    event_type: str | None
    session_id: str | None
    sensor: str | None
    src_ip: str | None
    src_port: int | None
    username: str | None
    command: str | None
    url: str | None
    sha256: str | None


@dataclass(frozen=True, slots=True)
class DownloadItem:
    timestamp: datetime | None
    url: str | None
    sha256: str | None


@dataclass(frozen=True, slots=True)
class SessionDetail:
    session: SessionListItem
    score: RiskScore | None
    commands: tuple[str, ...]
    downloads: tuple[DownloadItem, ...]
    events: tuple[EventListItem, ...]
