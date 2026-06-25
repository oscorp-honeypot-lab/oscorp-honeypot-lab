from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, SecretStr

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
