from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID


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
class TimelinePoint:
    timestamp: datetime
    events: int
    sessions: int


@dataclass(frozen=True, slots=True)
class SessionFilters:
    from_at: datetime | None = None
    to_at: datetime | None = None
    src_ip: str | None = None
    country: str | None = None
    username: str | None = None
    event_type: str | None = None
    risk_level: str | None = None
    reviewed: bool | None = None


@dataclass(frozen=True, slots=True)
class EventFilters:
    from_at: datetime | None = None
    to_at: datetime | None = None
    src_ip: str | None = None
    country: str | None = None
    username: str | None = None
    event_type: str | None = None


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
    country: str | None
    risk_score: int | None
    risk_level: str | None
    reviewed: bool
    reviewed_at: datetime | None
    reviewed_by: UUID | None
    reviewed_by_username: str | None


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
    country: str | None


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


@dataclass(frozen=True, slots=True)
class ExportArtifact:
    export_id: UUID
    filename: str
    content: bytes
    row_count: int
    total_rows: int
    page: int
    page_size: int
