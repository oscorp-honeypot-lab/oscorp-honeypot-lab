# Fase 33.5 — Consola LAB de simulaciones desde la app

## Objetivo

Convertir el LAB en una experiencia operable desde la aplicación web, sin requerir que el evaluador ejecute ataques y pipeline desde terminal.

## Arquitectura implementada

```
App web (React) → POST /api/v1/lab/run → LabService (FastAPI)
                                              ↓
                                    HTTP → lab-runner (attacker-sim:8888)
                                              ↓
                                    run_scenario.sh → cowrie
                                              ↓ (al completar)
                                    HTTP → pipeline-worker:8080/runs
                                              ↓
                                    Procesa eventos → alertas Telegram
```

## Componentes implementados

### 1. Migration `0015_lab_runs`

Tabla `lab_runs` con columnas: `id` (SERIAL), `scenario` (TEXT), `status` (TEXT), `actor` (TEXT), `started_at`, `finished_at`, `exit_code`, `log_text`, `error_detail`, `pipeline_events_read`, `pipeline_errors`. Check constraints en scenario (allowlist) y status.

Archivo: `pipeline/migrations/versions/0015_lab_runs.py`

### 2. lab-runner HTTP server

Servidor HTTP stdlib Python (sin dependencias externas) en puerto 8888 dentro de `attacker-sim`:
- `POST /run` — inicia un escenario en un hilo separado; rechaza con 409 si hay uno activo
- `GET /status` — devuelve `{status, exit_code, log}` del proceso en curso

Archivo: `attacker-sim/lab_runner.py`

### 3. Backend — LabService

`LabService.start_run()` valida:
- `OSCORP_API_ENVIRONMENT=lab` (rechaza en production/real)
- Scenario en allowlist `{brute-force, recon, malware-download, full}`
- No hay run activo en DB (status queued/running/processing)

Al pasar validaciones:
1. Crea `lab_run` con `status=queued`
2. Lanza background task `_run_background` con `asyncio.create_task`
3. Retorna 202 con el lab_run creado

Background task:
1. Llama `POST attacker-sim:8888/run`
2. Hace polling de `GET /status` cada 3s hasta completar
3. Llama `POST pipeline-worker:8080/runs` en modo incremental
4. Actualiza `lab_run` con status final, exit_code, log y métricas del pipeline

Archivo: `backend/app/application/lab_service.py`

### 4. API endpoints

- `POST /api/v1/lab/run` — requiere rol analyst/admin + CSRF → 202 con `LabRunResponse`
- `GET /api/v1/lab/status` — requiere viewer → 200 con run más reciente o 204
- `GET /api/v1/lab/logs/{run_id}` — requiere viewer → text/plain con log del run

Archivo: `backend/app/api/v1/lab.py`

### 5. Frontend

Página `LabPage` (container TanStack Query) + `LabView` (presentacional testeable):
- 4 botones de escenario con labels en español
- Polling cada 2s mientras status es queued/running/processing
- Botones deshabilitados si hay run activo o rol viewer
- Terminal monospace con log del run
- Badge de estado con color por status

Archivos:
- `frontend/src/features/lab/LabPage.tsx`
- `frontend/src/features/lab/LabView.tsx`

Ruta `/lab` agregada en `App.tsx`. Link "Laboratorio" en `AppShell.tsx`.

## Decisiones técnicas

- **Sin Docker socket**: El backend llama al lab-runner vía HTTP (attacker-sim:8888), no monta el socket Docker.
- **HTTP stdlib**: El lab-runner usa solo módulos estándar de Python (http.server, threading, subprocess) para no agregar dependencias externas a attacker-sim.
- **Allowlist estricta**: Validación doble — en LabService (Python) y en el lab-runner. El DB tiene CHECK CONSTRAINT adicional.
- **asyncio.to_thread**: Las llamadas HTTP bloqueantes del background task usan `asyncio.to_thread` para no bloquear el event loop.
- **CSRF en POST**: El endpoint POST /lab/run requiere token CSRF como el resto de endpoints de mutación.
- **Concurrencia vía DB**: El lock de concurrencia está en la capa de DB (query sobre status activo), no en memoria.

## Pruebas ejecutadas

### Backend — Unit tests (9 tests)
```
tests/unit/test_lab_service.py::test_start_run_rejected_when_not_lab_env PASSED
tests/unit/test_lab_service.py::test_start_run_rejected_when_not_lab_env_real_mode PASSED
tests/unit/test_lab_service.py::test_start_run_rejected_when_invalid_scenario PASSED
tests/unit/test_lab_service.py::test_start_run_rejected_when_empty_scenario PASSED
tests/unit/test_lab_service.py::test_start_run_rejected_when_concurrent_run_active PASSED
tests/unit/test_lab_service.py::test_start_run_rejected_when_queued_run_exists PASSED
tests/unit/test_lab_service.py::test_start_run_creates_lab_run_and_queues_task PASSED
tests/unit/test_lab_service.py::test_all_valid_scenarios_accepted PASSED
tests/unit/test_lab_service.py::test_get_status_returns_none_when_no_runs PASSED
```

### Backend — Integration tests (9 tests)
```
tests/integration/test_lab_api.py::test_post_run_requires_auth PASSED
tests/integration/test_lab_api.py::test_post_run_requires_analyst_role PASSED
tests/integration/test_lab_api.py::test_post_run_rejects_invalid_scenario PASSED
tests/integration/test_lab_api.py::test_post_run_returns_202_when_valid PASSED
tests/integration/test_lab_api.py::test_get_status_returns_204_when_no_runs PASSED
tests/integration/test_lab_api.py::test_get_status_returns_run PASSED
tests/integration/test_lab_api.py::test_post_run_returns_409_when_run_active PASSED
tests/integration/test_lab_api.py::test_get_logs_returns_text_for_run PASSED
tests/integration/test_lab_api.py::test_get_status_requires_auth PASSED
```

### Backend — Suite completa (76 tests)
```
76 passed, 1 warning
```

### Frontend — LabView tests (11 tests)
```
LabView > renders buttons for all 4 scenarios PASSED
LabView > disables buttons when status is running PASSED
LabView > disables buttons when status is queued PASSED
LabView > disables buttons when canRun is false (viewer role) PASSED
LabView > shows log text in terminal area when available PASSED
LabView > shows correct status badge for running PASSED
LabView > shows correct status badge for completed PASSED
LabView > calls onRun with the correct scenario key when a button is clicked PASSED
LabView > shows an error state with retry option PASSED
LabView > shows loading state PASSED
LabView > enables buttons when status is completed PASSED
```

### Frontend — Suite completa (23 tests)
```
23 passed (4 test files)
```

## Seguridad implementada

- Allowlist estricta de escenarios (no command injection posible)
- Solo disponible en `OSCORP_API_ENVIRONMENT=lab`
- Requiere rol `analyst` o `admin`
- Una sola ejecución concurrente (lock vía DB query)
- Sin Docker socket montado en backend
- Logs truncados a 50KB para evitar crecimiento indefinido
- El lab-runner (puerto 8888) solo es accesible dentro de la red Docker `oscorp_net`

## Archivos creados/modificados

### Nuevos
- `pipeline/migrations/versions/0015_lab_runs.py`
- `backend/app/application/lab_service.py`
- `backend/app/api/v1/lab.py`
- `backend/tests/unit/test_lab_service.py`
- `backend/tests/integration/test_lab_api.py`
- `attacker-sim/lab_runner.py`
- `frontend/src/features/lab/LabView.tsx`
- `frontend/src/features/lab/LabPage.tsx`
- `frontend/src/features/lab/LabView.test.tsx`

### Modificados
- `backend/app/domain/analytics.py` — agregado `LabRun` dataclass
- `backend/app/domain/ports/analytics_repository.py` — agregados métodos lab
- `backend/app/adapters/persistence/analytics_repository.py` — implementación lab
- `backend/app/infrastructure/config.py` — agregado `lab_runner_url`, `pipeline_worker_url`
- `backend/app/api/schemas.py` — agregado `LabRunRequest`, `LabRunResponse`
- `backend/app/api/dependencies.py` — agregado `get_lab_service`
- `backend/app/api/v1/router.py` — registrado lab router
- `backend/app/main.py` — inicialización `LabService`
- `attacker-sim/Dockerfile` — agregado `python3`
- `docker-compose.yml` — attacker-sim usa lab_runner, healthcheck agregado
- `frontend/src/app/App.tsx` — ruta `/lab`
- `frontend/src/components/AppShell.tsx` — enlace "Laboratorio"
- `frontend/src/api/client.ts` — funciones `getLabStatus`, `startLabRun`
- `scripts/validate_lab.ps1` — versión de migración `0015_lab_runs`
