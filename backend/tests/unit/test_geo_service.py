from __future__ import annotations

import pytest

from app.application.analytics_service import AnalyticsService
from app.domain.analytics import GeoCountryStat, GeoStats


class StubGeoRepository:
    def __init__(self, stats: GeoStats | None = None) -> None:
        self._stats = stats or GeoStats(
            total_with_geo=0,
            total_without_geo=0,
            unique_countries=0,
            by_country=(),
        )

    async def get_geo_stats(self) -> GeoStats:
        return self._stats

    def __getattr__(self, name: str):
        raise AttributeError(f"StubGeoRepository has no method '{name}'")


def _service(stats: GeoStats | None = None) -> AnalyticsService:
    return AnalyticsService(
        repository=StubGeoRepository(stats),  # type: ignore[arg-type]
        rules_version="1.1.0",
    )


@pytest.mark.anyio
async def test_geo_stats_returns_zeros_when_no_data() -> None:
    service = _service()
    stats = await service.get_geo_stats()
    assert stats.total_with_geo == 0
    assert stats.total_without_geo == 0
    assert stats.unique_countries == 0
    assert stats.by_country == ()


@pytest.mark.anyio
async def test_geo_stats_returns_country_breakdown() -> None:
    expected = GeoStats(
        total_with_geo=10,
        total_without_geo=5,
        unique_countries=3,
        by_country=(
            GeoCountryStat(
                country="China", country_code="CN",
                session_count=6, unique_ips=4,
            ),
            GeoCountryStat(
                country="Russia", country_code="RU",
                session_count=4, unique_ips=3,
            ),
        ),
    )
    service = _service(expected)
    stats = await service.get_geo_stats()
    assert stats.unique_countries == 3
    assert len(stats.by_country) == 2
    assert stats.by_country[0].country == "China"
    assert stats.by_country[0].session_count == 6


@pytest.mark.anyio
async def test_geo_stats_totals_are_consistent() -> None:
    expected = GeoStats(
        total_with_geo=20,
        total_without_geo=3,
        unique_countries=5,
        by_country=(),
    )
    service = _service(expected)
    stats = await service.get_geo_stats()
    assert stats.total_with_geo == 20
    assert stats.total_without_geo == 3
    assert stats.total_with_geo + stats.total_without_geo == 23
