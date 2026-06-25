from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.domain.health import HealthStatus, SystemHealth


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
