from __future__ import annotations

from typing import Protocol

from app.domain.health import DependencyHealth


class HealthRepository(Protocol):
    async def check(self) -> DependencyHealth: ...
