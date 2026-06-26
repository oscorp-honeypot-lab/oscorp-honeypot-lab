from __future__ import annotations

import pytest

from app.application.analytics_service import AnalyticsService
from app.domain.analytics import VtStats


class StubVtRepository:
    def __init__(self, stats: VtStats | None = None) -> None:
        self._stats = stats or VtStats(
            total_cached=0,
            malicious_detected=0,
            not_found=0,
            error_count=0,
            max_malicious=None,
        )

    async def get_vt_stats(self) -> VtStats:
        return self._stats

    def __getattr__(self, name: str):
        raise AttributeError(f"StubVtRepository has no method '{name}'")


def _service(stats: VtStats | None = None) -> AnalyticsService:
    return AnalyticsService(
        repository=StubVtRepository(stats),  # type: ignore[arg-type]
        rules_version="1.0.0",
    )


@pytest.mark.anyio
async def test_vt_stats_returns_zeros_when_empty() -> None:
    service = _service()
    stats = await service.get_vt_stats()
    assert stats.total_cached == 0
    assert stats.malicious_detected == 0
    assert stats.max_malicious is None


@pytest.mark.anyio
async def test_vt_stats_returns_values_from_repository() -> None:
    expected = VtStats(
        total_cached=5,
        malicious_detected=3,
        not_found=1,
        error_count=1,
        max_malicious=47,
    )
    service = _service(expected)
    stats = await service.get_vt_stats()
    assert stats.total_cached == 5
    assert stats.malicious_detected == 3
    assert stats.max_malicious == 47


@pytest.mark.anyio
async def test_vt_stats_error_count_included() -> None:
    expected = VtStats(
        total_cached=10,
        malicious_detected=0,
        not_found=2,
        error_count=3,
        max_malicious=None,
    )
    service = _service(expected)
    stats = await service.get_vt_stats()
    assert stats.not_found == 2
    assert stats.error_count == 3
