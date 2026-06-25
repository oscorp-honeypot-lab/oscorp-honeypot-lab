from __future__ import annotations

import pytest

from app.application.health_service import HealthService
from app.domain.health import DependencyHealth, HealthStatus


class StubRepository:
    def __init__(self, status: HealthStatus) -> None:
        self._status = status

    async def check(self) -> DependencyHealth:
        return DependencyHealth(name="postgres", status=self._status)


@pytest.mark.asyncio
async def test_ready_is_ok_when_database_is_available() -> None:
    service = HealthService(
        StubRepository(HealthStatus.OK),
        service_name="test-api",
        version="1.0.0",
    )

    health = await service.ready()

    assert health.status is HealthStatus.OK
    assert health.dependencies[0].name == "postgres"


@pytest.mark.asyncio
async def test_ready_is_degraded_when_database_is_unavailable() -> None:
    service = HealthService(
        StubRepository(HealthStatus.DEGRADED),
        service_name="test-api",
        version="1.0.0",
    )

    health = await service.ready()

    assert health.status is HealthStatus.DEGRADED
