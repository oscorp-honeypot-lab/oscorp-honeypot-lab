from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
import uuid
from typing import Any

from app.domain.analytics import LabRun
from app.domain.ports.analytics_repository import AnalyticsRepository

ALLOWED_SCENARIOS = frozenset({"brute-force", "recon", "malware-download", "full"})
_LOG_LIMIT = 50_000


class LabEnvironmentRequired(Exception):
    pass


class LabScenarioInvalid(Exception):
    pass


class LabRunConflict(Exception):
    pass


def _http_post(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_get(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


class LabService:
    def __init__(
        self,
        repository: AnalyticsRepository,
        environment: str,
        lab_runner_url: str = "http://attacker-sim:8888",
        pipeline_worker_url: str = "http://pipeline-worker:8080",
    ) -> None:
        self._repository = repository
        self._environment = environment
        self._lab_runner_url = lab_runner_url
        self._pipeline_worker_url = pipeline_worker_url

    async def start_run(self, *, scenario: str, actor: str) -> LabRun:
        if self._environment.lower() not in {"lab"}:
            raise LabEnvironmentRequired(
                f"Lab console is only available in lab environment, got: {self._environment}"
            )
        if scenario not in ALLOWED_SCENARIOS:
            raise LabScenarioInvalid(f"Unknown scenario: {scenario!r}")
        active = await self._repository.get_active_lab_run()
        if active is not None:
            raise LabRunConflict(f"Another lab run is active: id={active.id} status={active.status}")
        run = await self._repository.create_lab_run(scenario=scenario, actor=actor)
        asyncio.create_task(self._run_background(run.id, scenario))
        return run

    async def get_status(self) -> LabRun | None:
        return await self._repository.get_latest_lab_run()

    async def get_logs(self, *, run_id: int) -> str:
        run = await self._repository.get_lab_run(run_id=run_id)
        if run is None:
            return ""
        return run.log_text or ""

    async def _run_background(self, run_id: int, scenario: str) -> None:
        log_lines: list[str] = []

        async def _update(
            *,
            status: str,
            exit_code: int | None = None,
            pipeline_events_read: int | None = None,
            pipeline_errors: int | None = None,
            error_detail: str | None = None,
            set_finished: bool = False,
        ) -> None:
            try:
                await self._repository.update_lab_run(
                    run_id=run_id,
                    status=status,
                    log_text="\n".join(log_lines)[:_LOG_LIMIT],
                    error_detail=error_detail,
                    exit_code=exit_code,
                    pipeline_events_read=pipeline_events_read,
                    pipeline_errors=pipeline_errors,
                    set_finished=set_finished,
                )
            except Exception:
                pass

        try:
            log_lines.append(f"[lab] iniciando escenario {scenario}")
            await _update(status="running")

            try:
                await asyncio.to_thread(
                    _http_post,
                    f"{self._lab_runner_url}/run",
                    {"scenario": scenario},
                )
            except Exception as exc:
                raise RuntimeError(f"lab-runner no disponible: {exc}") from exc

            exit_code: int | None = None
            runner_log = ""
            for _ in range(200):
                await asyncio.sleep(3)
                try:
                    status_data = await asyncio.to_thread(
                        _http_get,
                        f"{self._lab_runner_url}/status",
                    )
                    runner_log = status_data.get("log", "")
                    runner_status = status_data.get("status", "running")
                    exit_code = status_data.get("exit_code")
                    if runner_status in ("completed", "failed"):
                        break
                except Exception:
                    pass

            if runner_log:
                for line in runner_log.splitlines():
                    log_lines.append(line)

            log_lines.append("[pipeline] iniciando procesamiento...")
            await _update(status="processing")

            events_read = 0
            errors_count = 0
            try:
                pipeline_result = await asyncio.to_thread(
                    _http_post,
                    f"{self._pipeline_worker_url}/runs",
                    {
                        "contract_version": "1.0",
                        "request_id": str(uuid.uuid4()),
                        "triggered_by": "n8n_manual",
                        "mode": "incremental",
                        "source": "cowrie_ndjson",
                    },
                )
                events_read = int(pipeline_result.get("events_read", 0))
                errors_count = int(pipeline_result.get("errors_count", 0))
            except Exception as exc:
                log_lines.append(f"[pipeline] advertencia: {exc}")

            log_lines.append(f"[pipeline] events_read={events_read}")
            if errors_count:
                log_lines.append(f"[pipeline] errors={errors_count}")
            log_lines.append("[lab] completado")

            await _update(
                status="completed",
                exit_code=exit_code,
                pipeline_events_read=events_read,
                pipeline_errors=errors_count,
                set_finished=True,
            )

        except Exception as exc:
            log_lines.append(f"[lab] error: {exc}")
            await _update(
                status="failed",
                error_detail=str(exc)[:2048],
                set_finished=True,
            )
