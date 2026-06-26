from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.application.lab_service import (
    LabEnvironmentRequired,
    LabRunConflict,
    LabScenarioInvalid,
    LabService,
)
from app.domain.analytics import LabRun


def _make_run(
    *,
    status: str = "queued",
    run_id: int = 1,
    scenario: str = "brute-force",
) -> LabRun:
    return LabRun(
        id=run_id,
        scenario=scenario,
        status=status,
        actor="analyst",
        started_at=datetime(2026, 6, 26, tzinfo=timezone.utc),
        finished_at=None,
        exit_code=None,
        log_text=None,
        error_detail=None,
        pipeline_events_read=None,
        pipeline_errors=None,
    )


class _FakeRepo:
    def __init__(self, *, active_run: LabRun | None = None) -> None:
        self.created: list[dict] = []
        self.updates: list[dict] = []
        self._active_run = active_run

    async def get_active_lab_run(self) -> LabRun | None:
        return self._active_run

    async def create_lab_run(self, *, scenario: str, actor: str) -> LabRun:
        self.created.append({"scenario": scenario, "actor": actor})
        return _make_run(scenario=scenario)

    async def update_lab_run(self, *, run_id: int, **fields: object) -> None:
        self.updates.append({"run_id": run_id, **fields})

    async def get_latest_lab_run(self) -> LabRun | None:
        return None

    async def get_lab_run(self, *, run_id: int) -> LabRun | None:
        return None


def _make_service(
    *,
    environment: str = "lab",
    active_run: LabRun | None = None,
    lab_runner_url: str = "http://attacker-sim:8888",
    pipeline_worker_url: str = "http://pipeline-worker:8080",
) -> tuple[LabService, _FakeRepo]:
    repo = _FakeRepo(active_run=active_run)
    service = LabService(
        repository=repo,
        environment=environment,
        lab_runner_url=lab_runner_url,
        pipeline_worker_url=pipeline_worker_url,
    )
    return service, repo


@pytest.mark.asyncio
async def test_start_run_rejected_when_not_lab_env() -> None:
    service, _ = _make_service(environment="production")
    with pytest.raises(LabEnvironmentRequired):
        await service.start_run(scenario="brute-force", actor="analyst")


@pytest.mark.asyncio
async def test_start_run_rejected_when_not_lab_env_real_mode() -> None:
    service, _ = _make_service(environment="real")
    with pytest.raises(LabEnvironmentRequired):
        await service.start_run(scenario="recon", actor="analyst")


@pytest.mark.asyncio
async def test_start_run_rejected_when_invalid_scenario() -> None:
    service, _ = _make_service()
    with pytest.raises(LabScenarioInvalid):
        await service.start_run(scenario="arbitrary-command", actor="analyst")


@pytest.mark.asyncio
async def test_start_run_rejected_when_empty_scenario() -> None:
    service, _ = _make_service()
    with pytest.raises(LabScenarioInvalid):
        await service.start_run(scenario="", actor="analyst")


@pytest.mark.asyncio
async def test_start_run_rejected_when_concurrent_run_active() -> None:
    active = _make_run(status="running")
    service, _ = _make_service(active_run=active)
    with pytest.raises(LabRunConflict):
        await service.start_run(scenario="brute-force", actor="analyst")


@pytest.mark.asyncio
async def test_start_run_rejected_when_queued_run_exists() -> None:
    active = _make_run(status="queued")
    service, _ = _make_service(active_run=active)
    with pytest.raises(LabRunConflict):
        await service.start_run(scenario="recon", actor="analyst")


@pytest.mark.asyncio
async def test_start_run_creates_lab_run_and_queues_task() -> None:
    service, repo = _make_service()
    background_called: list[tuple[int, str]] = []

    async def _fake_background(run_id: int, scenario: str) -> None:
        background_called.append((run_id, scenario))

    service._run_background = _fake_background

    result = await service.start_run(scenario="full", actor="admin")

    assert result.scenario == "full"
    assert result.status == "queued"
    assert len(repo.created) == 1
    assert repo.created[0]["scenario"] == "full"
    assert repo.created[0]["actor"] == "admin"

    await asyncio.sleep(0)
    assert len(background_called) == 1
    assert background_called[0] == (result.id, "full")


@pytest.mark.asyncio
async def test_all_valid_scenarios_accepted() -> None:
    for scenario in ("brute-force", "recon", "malware-download", "full"):
        service, repo = _make_service()
        async def _noop(run_id: int, s: str) -> None:
            pass
        service._run_background = _noop
        result = await service.start_run(scenario=scenario, actor="analyst")
        assert result.scenario == scenario


@pytest.mark.asyncio
async def test_get_status_returns_none_when_no_runs() -> None:
    service, _ = _make_service()
    result = await service.get_status()
    assert result is None
