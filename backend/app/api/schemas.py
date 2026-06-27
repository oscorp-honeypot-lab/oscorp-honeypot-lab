from __future__ import annotations

from datetime import datetime
from math import ceil
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.domain.analytics import (
    AlertItem,
    AnalyticsSummary,
    EventListItem,
    GeoCountryStat,
    GeoStats,
    LabRun,
    MttdStats,
    Page,
    ReportDelivery,
    ReportRun,
    SessionDetail,
    SessionListItem,
    TimelinePoint,
    VtStats,
)
from app.domain.health import HealthStatus, SystemHealth
from app.domain.identity import Role, UserIdentity


class DependencyHealthResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    status: HealthStatus
    latency_ms: float | None = None
    detail: str | None = None


class HealthResponse(BaseModel):
    status: HealthStatus
    service: str
    version: str
    dependencies: tuple[DependencyHealthResponse, ...] = ()

    @classmethod
    def from_domain(cls, health: SystemHealth) -> "HealthResponse":
        return cls.model_validate(
            {
                "status": health.status,
                "service": health.service,
                "version": health.version,
                "dependencies": health.dependencies,
            }
        )


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: SecretStr = Field(min_length=1, max_length=128)


class UserCreateRequest(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_.-]+$",
    )
    password: SecretStr = Field(min_length=12, max_length=128)
    role: Role


class UserResponse(BaseModel):
    id: str
    username: str
    role: Role

    @classmethod
    def from_domain(cls, user: UserIdentity) -> "UserResponse":
        return cls(id=str(user.id), username=user.username, role=user.role)


class LoginResponse(BaseModel):
    user: UserResponse
    expires_at: str


class AnalyticsSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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

    @classmethod
    def from_domain(cls, summary: AnalyticsSummary) -> "AnalyticsSummaryResponse":
        return cls.model_validate(summary)


class TimelinePointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    events: int
    sessions: int


class TimelineResponse(BaseModel):
    hours: int
    points: tuple[TimelinePointResponse, ...]

    @classmethod
    def from_domain(
        cls,
        *,
        hours: int,
        points: tuple[TimelinePoint, ...],
    ) -> "TimelineResponse":
        return cls(
            hours=hours,
            points=tuple(
                TimelinePointResponse.model_validate(point) for point in points
            ),
        )


class SessionListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class EventListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class PaginationResponse(BaseModel):
    page: int
    page_size: int
    total: int
    pages: int

    @classmethod
    def from_page(cls, page: Page[object]) -> "PaginationResponse":
        return cls(
            page=page.page,
            page_size=page.page_size,
            total=page.total,
            pages=ceil(page.total / page.page_size) if page.total else 0,
        )


class SessionPageResponse(BaseModel):
    items: tuple[SessionListItemResponse, ...]
    pagination: PaginationResponse

    @classmethod
    def from_domain(cls, page: Page[SessionListItem]) -> "SessionPageResponse":
        return cls(
            items=tuple(
                SessionListItemResponse.model_validate(item) for item in page.items
            ),
            pagination=PaginationResponse.from_page(page),
        )


class EventPageResponse(BaseModel):
    items: tuple[EventListItemResponse, ...]
    pagination: PaginationResponse

    @classmethod
    def from_domain(cls, page: Page[EventListItem]) -> "EventPageResponse":
        return cls(
            items=tuple(
                EventListItemResponse.model_validate(item) for item in page.items
            ),
            pagination=PaginationResponse.from_page(page),
        )


class RiskScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    score: int
    level: str
    reasons: tuple[dict[str, object], ...]
    rules_version: str
    calculated_at: datetime


class DownloadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime | None
    url: str | None
    sha256: str | None


class SessionDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session: SessionListItemResponse
    score: RiskScoreResponse | None
    commands: tuple[str, ...]
    downloads: tuple[DownloadResponse, ...]
    events: tuple[EventListItemResponse, ...]

    @classmethod
    def from_domain(cls, detail: SessionDetail) -> "SessionDetailResponse":
        return cls.model_validate(detail)


class SessionReviewRequest(BaseModel):
    reviewed: bool


class MttdTriggerStatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trigger: str
    avg_seconds: float
    min_seconds: float
    max_seconds: float
    count: int


class MttdStatsResponse(BaseModel):
    avg_seconds: float | None
    min_seconds: float | None
    max_seconds: float | None
    p95_seconds: float | None
    total_sent: int
    total_failed: int
    total_pending: int
    failure_rate: float
    by_trigger: tuple[MttdTriggerStatResponse, ...]

    @classmethod
    def from_domain(cls, stats: MttdStats) -> "MttdStatsResponse":
        return cls(
            avg_seconds=stats.avg_seconds,
            min_seconds=stats.min_seconds,
            max_seconds=stats.max_seconds,
            p95_seconds=stats.p95_seconds,
            total_sent=stats.total_sent,
            total_failed=stats.total_failed,
            total_pending=stats.total_pending,
            failure_rate=stats.failure_rate,
            by_trigger=tuple(
                MttdTriggerStatResponse.model_validate(t) for t in stats.by_trigger
            ),
        )


class VtStatsResponse(BaseModel):
    total_cached: int
    malicious_detected: int
    not_found: int
    error_count: int
    max_malicious: int | None

    @classmethod
    def from_domain(cls, stats: VtStats) -> "VtStatsResponse":
        return cls(
            total_cached=stats.total_cached,
            malicious_detected=stats.malicious_detected,
            not_found=stats.not_found,
            error_count=stats.error_count,
            max_malicious=stats.max_malicious,
        )


class GeoCountryStatResponse(BaseModel):
    country: str
    country_code: str | None
    session_count: int
    unique_ips: int

    @classmethod
    def from_domain(cls, stat: GeoCountryStat) -> "GeoCountryStatResponse":
        return cls(
            country=stat.country,
            country_code=stat.country_code,
            session_count=stat.session_count,
            unique_ips=stat.unique_ips,
        )


class GeoStatsResponse(BaseModel):
    total_with_geo: int
    total_without_geo: int
    unique_countries: int
    by_country: list[GeoCountryStatResponse]

    @classmethod
    def from_domain(cls, stats: GeoStats) -> "GeoStatsResponse":
        return cls(
            total_with_geo=stats.total_with_geo,
            total_without_geo=stats.total_without_geo,
            unique_countries=stats.unique_countries,
            by_country=[
                GeoCountryStatResponse.from_domain(c) for c in stats.by_country
            ],
        )


class AlertItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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

    @classmethod
    def from_domain(cls, alert: "AlertItem") -> "AlertItemResponse":
        return cls.model_validate(alert)


class AlertPageResponse(BaseModel):
    items: tuple[AlertItemResponse, ...]
    pagination: PaginationResponse

    @classmethod
    def from_domain(cls, page: "Page[AlertItem]") -> "AlertPageResponse":
        return cls(
            items=tuple(AlertItemResponse.from_domain(item) for item in page.items),
            pagination=PaginationResponse.from_page(page),
        )


class ReportRunResponse(BaseModel):
    id: UUID
    period_type: str
    period_start: datetime
    period_end: datetime
    status: str
    dataset: dict[str, object]

    @classmethod
    def from_domain(cls, report: ReportRun) -> "ReportRunResponse":
        return cls(
            id=report.id,
            period_type=report.period_type,
            period_start=report.period_start,
            period_end=report.period_end,
            status=report.status,
            dataset=report.dataset,
        )


class ReportDeliveryResponse(BaseModel):
    id: UUID
    report_id: UUID
    channel: str
    format: str
    status: str
    filename: str | None
    error_code: str | None

    @classmethod
    def from_domain(cls, delivery: ReportDelivery) -> "ReportDeliveryResponse":
        return cls(
            id=delivery.id,
            report_id=delivery.report_id,
            channel=delivery.channel,
            format=delivery.format,
            status=delivery.status,
            filename=delivery.filename,
            error_code=delivery.error_code,
        )


class LabRunRequest(BaseModel):
    scenario: str = Field(min_length=1, max_length=64)


class LabRunResponse(BaseModel):
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

    @classmethod
    def from_domain(cls, run: LabRun) -> "LabRunResponse":
        return cls(
            id=run.id,
            scenario=run.scenario,
            status=run.status,
            actor=run.actor,
            started_at=run.started_at,
            finished_at=run.finished_at,
            exit_code=run.exit_code,
            log_text=run.log_text,
            error_detail=run.error_detail,
            pipeline_events_read=run.pipeline_events_read,
            pipeline_errors=run.pipeline_errors,
        )
