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
    source_mode: str | None = None
    sort_by: str = "last_event_at"
    sort_order: str = "desc"


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
    source_mode: str


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
class MttdTriggerStat:
    trigger: str
    avg_seconds: float
    min_seconds: float
    max_seconds: float
    count: int


@dataclass(frozen=True, slots=True)
class MttdStats:
    avg_seconds: float | None
    min_seconds: float | None
    max_seconds: float | None
    p95_seconds: float | None
    total_sent: int
    total_failed: int
    total_pending: int
    failure_rate: float
    by_trigger: tuple[MttdTriggerStat, ...]


@dataclass(frozen=True, slots=True)
class VtStats:
    total_cached: int
    malicious_detected: int
    not_found: int
    error_count: int
    max_malicious: int | None


@dataclass(frozen=True, slots=True)
class GeoCountryStat:
    country: str
    country_code: str | None
    session_count: int
    unique_ips: int


@dataclass(frozen=True, slots=True)
class GeoStats:
    total_with_geo: int
    total_without_geo: int
    unique_countries: int
    by_country: tuple[GeoCountryStat, ...]


@dataclass(frozen=True, slots=True)
class AlertItem:
    id: UUID
    session_key: str
    trigger: str
    channel: str
    status: str
    risk_level: str | None
    risk_score: int | None
    event_timestamp: datetime | None
    triggered_at: datetime
    sent_at: datetime | None
    mttd_seconds: float | None
    error_code: str | None
    error_detail: str | None


@dataclass(frozen=True, slots=True)
class ExportArtifact:
    export_id: UUID
    filename: str
    content: bytes
    row_count: int
    total_rows: int
    page: int
    page_size: int


@dataclass(frozen=True, slots=True)
class ReportRun:
    id: UUID
    period_type: str
    period_start: datetime
    period_end: datetime
    status: str
    dataset: dict[str, object]


@dataclass(frozen=True, slots=True)
class ReportArtifact:
    delivery_id: UUID
    report_id: UUID
    period_type: str
    filename: str
    media_type: str
    content: bytes


@dataclass(frozen=True, slots=True)
class ReportDelivery:
    id: UUID
    report_id: UUID
    channel: str
    format: str
    status: str
    filename: str | None
    error_code: str | None


@dataclass(frozen=True, slots=True)
class LabRun:
    id: int
    scenario: str
    status: str
    actor: str
    started_at: datetime
    finished_at: datetime | None
    exit_code: int | None
    log_text: str | None
    error_detail: str | None
    pipeline_events_read: int | None
    pipeline_errors: int | None
