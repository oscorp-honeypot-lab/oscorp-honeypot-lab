from __future__ import annotations

from datetime import datetime
from math import ceil
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.domain.analytics import (
    AnalyticsSummary,
    EventListItem,
    Page,
    SessionDetail,
    SessionListItem,
    TimelinePoint,
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
