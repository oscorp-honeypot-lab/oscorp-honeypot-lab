from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class HealthStatus(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"


@dataclass(frozen=True, slots=True)
class DependencyHealth:
    name: str
    status: HealthStatus
    latency_ms: float | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class SystemHealth:
    status: HealthStatus
    service: str
    version: str
    dependencies: tuple[DependencyHealth, ...] = ()
