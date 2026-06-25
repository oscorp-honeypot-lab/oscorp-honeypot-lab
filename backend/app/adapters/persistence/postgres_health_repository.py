from __future__ import annotations

from time import perf_counter

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.health import DependencyHealth, HealthStatus


class PostgresHealthRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def check(self) -> DependencyHealth:
        started_at = perf_counter()
        try:
            async with self._session_factory() as session:
                await session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return DependencyHealth(
                name="postgres",
                status=HealthStatus.DEGRADED,
                detail="database_unavailable",
            )
        return DependencyHealth(
            name="postgres",
            status=HealthStatus.OK,
            latency_ms=round((perf_counter() - started_at) * 1000, 2),
        )
