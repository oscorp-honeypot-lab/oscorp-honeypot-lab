# Fase 30 - Motor de reportes periodicos

Fecha: 26 de junio de 2026.

## Alcance

```text
[x] Motor Python para datasets diarios y semanales cerrados.
[x] Ventanas UTC idempotentes:
    - daily: dia UTC completo anterior
    - weekly: semana ISO completa anterior (lunes a lunes)
[x] Persistencia en report_runs mediante migracion Alembic 0013.
[x] Dataset JSONB con eventos, IPs, sesiones, paises, credenciales,
    comandos, descargas, hashes maliciosos, sesiones criticas, MTTD y
    alertas fallidas.
[x] Programacion en n8n:
    - Daily Report Schedule: diario 03:00
    - Weekly Report Schedule: lunes 03:15
    Ambos invocan el worker con triggered_by=n8n_schedule.
[x] Integracion en execute_pipeline(): genera reportes aunque el lote
    incremental no tenga eventos nuevos.
[x] 5 pruebas unitarias nuevas para ventanas, dataset, filtros por periodo,
    upsert idempotente y generacion daily+weekly.
```

## Skills

```text
buscados:
- periodic reports backend scheduled workflow database testing

utilizados:
- python-expert-best-practices-code-review
- sqlalchemy-alembic-expert-best-practices-code-review
- n8n-error-handling

instalados: ninguno

descartados:
- insforge-cli, celery, async-jobs y similares: genericos o fuera del alcance
  del stack actual. El repo ya tiene worker HTTP privado, n8n y PostgreSQL.
```

## Implementacion

```text
Tabla report_runs:
  id UUID
  pipeline_run_id FK opcional
  period_type daily|weekly
  period_start / period_end
  status completed|failed
  dataset JSONB
  error_code / error_detail
  started_at / finished_at

Indices:
  uq_report_runs_period (period_type, period_start, period_end)
  idx_report_runs_status_started (status, started_at)

Motor:
  closed_report_periods(reference_at)
  build_report_dataset(connection, period)
  store_report_run(connection, period, dataset)
  generate_scheduled_reports(connection, reference_at, pipeline_run_id)
```

El dataset se calcula con consultas directas sobre las tablas operativas:

```text
eventos:
  eventos totales, IPs unicas, top IPs, credenciales, comandos y descargas.

sessions + ip_geo_cache:
  sesiones del periodo y top paises.

vt_hash_cache:
  hashes descargados con reputacion maliciosa vigente.

session_risk_scores:
  sesiones criticas usando rules_version 1.1.0.

alerts:
  MTTD agregado y alertas fallidas por error_code.
```

## Archivos creados o modificados

```text
pipeline/migrations/versions/0013_report_runs.py
pipeline/reports/__init__.py
pipeline/reports/engine.py
pipeline/tests/test_reports_engine.py
scripts/process_cowrie_ndjson.py
pipeline/Dockerfile
n8n/workflows/oscorp-workflow.json
ESTADO_Y_ROADMAP.md
docs/evidencias/fase30_motor_reportes_periodicos.md
```

## TDD Cycle Evidence

| Task | Test File | Layer | RED | GREEN | TRIANGULATE |
|------|-----------|-------|-----|-------|-------------|
| ventanas cerradas daily/weekly | test_reports_engine.py | Unit | nuevo modulo ausente | 1/1 | viernes 2026-06-26 -> dia 25 y semana 15-22 |
| dataset de fase 30 | test_reports_engine.py | Unit | secciones ausentes | 1/1 | eventos, IPs, sesiones, paises, credenciales, comandos, descargas, VT, criticas, MTTD, fallos |
| filtros por periodo | test_reports_engine.py | Unit | sin contratos de parametros | 1/1 | todas las consultas reciben start/end |
| upsert idempotente | test_reports_engine.py | Unit | report_runs ausente | 1/1 | ON CONFLICT por periodo |
| generacion programada | test_reports_engine.py | Unit | sin scheduler interno | 1/1 | daily + weekly guardados |

## Validacion

```text
python -m json.tool n8n/workflows/oscorp-workflow.json
resultado: OK

python -m py_compile pipeline/reports/engine.py \
    pipeline/migrations/versions/0013_report_runs.py \
    scripts/process_cowrie_ndjson.py
resultado: OK

python -m unittest tests.test_reports_engine
resultado: 5/5 OK
```

Validacion contenerizada:

```text
docker compose build migrate
resultado: OK

docker compose run --rm --no-deps migrate python -m unittest discover -s /app/tests
resultado: 133/133 OK

docker compose --profile lab run --rm migrate
resultado: Alembic upgrade hasta 0013_report_runs OK

./scripts/validate_n8n_contract.ps1
resultado: contrato, worker y orquestacion n8n validados; workflow versionado
importado correctamente.

SELECT version_num FROM alembic_version;
resultado: 0013_report_runs

SELECT to_regclass('public.report_runs');
resultado: report_runs
```

Validacion end-to-end del worker:

```text
execute_pipeline(
  request_id='00000000-0000-4000-8000-000000000032',
  triggered_by='n8n_schedule',
  mode='incremental'
)

resultado:
  run_id: 103
  status: completed
  events_read: 0
  errors_count: 0

report_runs:
  daily  2026-06-25 00:00:00+00 -> 2026-06-26 00:00:00+00 completed
  weekly 2026-06-15 00:00:00+00 -> 2026-06-22 00:00:00+00 completed

Ambos datasets incluyen totals, mttd y failed_alerts.
```

Conclusion:

```text
La Fase 30 queda implementada y validada en el entorno Docker LAB.
Durante la primera validacion end-to-end se detecto y corrigio un error de
sintaxis SQL en agregados FILTER con cast; la corrida posterior finalizo OK.
```
