from __future__ import annotations

import pytest

from app.application.analytics_service import AnalyticsService
from app.domain.analytics import MttdStats, MttdTriggerStat


class StubMttdRepository:
    def __init__(self, stats: MttdStats | None = None) -> None:
        self._stats = stats or MttdStats(
            avg_seconds=None,
            min_seconds=None,
            max_seconds=None,
            p95_seconds=None,
            total_sent=0,
            total_failed=0,
            total_pending=0,
            failure_rate=0.0,
            by_trigger=(),
        )

    async def get_mttd_stats(self) -> MttdStats:
        return self._stats

    def __getattr__(self, name: str):
        raise AttributeError(f"StubMttdRepository has no method '{name}'")


def _service(stats: MttdStats | None = None) -> AnalyticsService:
    return AnalyticsService(
        repository=StubMttdRepository(stats),  # type: ignore[arg-type]
        rules_version="1.0.0",
    )


@pytest.mark.anyio
async def test_get_mttd_stats_returns_empty_when_no_sent_alerts() -> None:
    service = _service()
    stats = await service.get_mttd_stats()
    assert stats.total_sent == 0
    assert stats.avg_seconds is None
    assert stats.by_trigger == ()


@pytest.mark.anyio
async def test_get_mttd_stats_returns_aggregated_values() -> None:
    expected = MttdStats(
        avg_seconds=1200.0,
        min_seconds=300.0,
        max_seconds=3600.0,
        p95_seconds=3200.0,
        total_sent=10,
        total_failed=2,
        total_pending=1,
        failure_rate=0.1667,
        by_trigger=(
            MttdTriggerStat(
                trigger="high_risk",
                avg_seconds=1500.0,
                min_seconds=500.0,
                max_seconds=3600.0,
                count=5,
            ),
        ),
    )
    service = _service(expected)
    stats = await service.get_mttd_stats()
    assert stats.avg_seconds == 1200.0
    assert stats.p95_seconds == 3200.0
    assert stats.total_sent == 10
    assert stats.total_failed == 2
    assert stats.failure_rate == pytest.approx(0.1667)
    assert len(stats.by_trigger) == 1
    assert stats.by_trigger[0].trigger == "high_risk"


@pytest.mark.anyio
async def test_failure_rate_is_zero_when_no_alerts_processed() -> None:
    service = _service()
    stats = await service.get_mttd_stats()
    assert stats.failure_rate == 0.0


@pytest.mark.anyio
async def test_by_trigger_contains_all_trigger_types() -> None:
    stats = MttdStats(
        avg_seconds=1000.0,
        min_seconds=100.0,
        max_seconds=5000.0,
        p95_seconds=4000.0,
        total_sent=9,
        total_failed=0,
        total_pending=0,
        failure_rate=0.0,
        by_trigger=(
            MttdTriggerStat("file_download", 800.0, 100.0, 2000.0, 3),
            MttdTriggerStat("high_risk", 1200.0, 300.0, 5000.0, 3),
            MttdTriggerStat("successful_login", 1000.0, 200.0, 3000.0, 3),
        ),
    )
    service = _service(stats)
    result = await service.get_mttd_stats()
    triggers = {t.trigger for t in result.by_trigger}
    assert "high_risk" in triggers
    assert "successful_login" in triggers
    assert "file_download" in triggers
