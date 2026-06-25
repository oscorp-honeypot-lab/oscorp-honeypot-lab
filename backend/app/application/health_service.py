from __future__ import annotations

from app.domain.health import HealthStatus, SystemHealth
from app.domain.ports.health_repository import HealthRepository


class HealthService:
    def __init__(
        self,
        repository: HealthRepository,
        *,
        service_name: str,
        version: str,
    ) -> None:
        self._repository = repository
        self._service_name = service_name
        self._version = version

    def live(self) -> SystemHealth:
        return SystemHealth(
            status=HealthStatus.OK,
            service=self._service_name,
            version=self._version,
        )

    async def ready(self) -> SystemHealth:
        dependency = await self._repository.check()
        return SystemHealth(
            status=(
                HealthStatus.OK
                if dependency.status is HealthStatus.OK
                else HealthStatus.DEGRADED
            ),
            service=self._service_name,
            version=self._version,
            dependencies=(dependency,),
        )
