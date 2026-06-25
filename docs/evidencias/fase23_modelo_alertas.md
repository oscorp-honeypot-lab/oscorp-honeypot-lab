# Fase 23 - Modelo y políticas de alertas

Fecha: 25 de junio de 2026.

## Alcance

```text
[x] Migración 0009_alerts_model — reemplaza tabla alerts básica de 0001
[x] Tabla alerts con UUID PK, session_key FK, event_hash FK, pipeline_run_id FK
[x] Campos trigger, channel, status, risk_level, risk_score, timestamps, MTTD, error
[x] CHECK constraints: trigger, channel, status, risk_score
[x] UNIQUE(session_key, trigger) — deduplicación automática
[x] Índices: session_key, (status, triggered_at), triggered_at
[x] pipeline/alerts/criteria.py — motor de criterios puro sin DB
[x] pipeline/alerts/storage.py — persistencia con deduplicación ON CONFLICT DO NOTHING
[x] Integración en scripts/process_cowrie_ndjson.py post recalculate_scores
[x] backend/app/domain/analytics.py — AlertItem dataclass
[x] backend/app/api/schemas.py — AlertItemResponse + AlertPageResponse
[x] backend/app/api/v1/alerts.py — GET /api/v1/alerts con filtros status y sessionKey
[x] Paginación, autenticación (rol viewer mínimo)
[x] 12 alertas generadas end-to-end desde sesiones existentes
```

## Skills

```text
buscados:
- Alembic ALTER/DROP TABLE patterns
- psycopg executemany deduplication
- FastAPI pagination with optional query filters

utilizados existentes:
- psycopg (INSERT ON CONFLICT DO NOTHING)
- Alembic (op.drop_table + op.create_table + autocommit_block)
- FastAPI (APIRouter, Query, Depends)
- SQLAlchemy text() queries

instalados:
- ninguno
```

## Implementación

```text
criterios de alerta:
- high_risk:         risk_level IN ('high', 'critical')
- successful_login:  has_successful_login = true
- file_download:     has_download = true

canal default: telegram (pending — envío real en Fase 24)
estados: pending / sent / failed / suppressed
deduplicación: UNIQUE(session_key, trigger) → ON CONFLICT DO NOTHING

integración pipeline:
  recalculate_scores(connection, session_keys)
  generate_session_alerts(connection, session_keys, run_id)  ← nuevo

backend API:
  GET /api/v1/alerts?page=1&pageSize=50&status=pending&sessionKey=xxx
  requiere rol viewer o superior
  respuesta paginada con AlertItemResponse
```

Archivos creados o modificados:

```text
pipeline/migrations/versions/0009_alerts_model.py      (nuevo)
pipeline/alerts/__init__.py                            (nuevo)
pipeline/alerts/criteria.py                            (nuevo)
pipeline/alerts/storage.py                             (nuevo)
pipeline/tests/test_alert_criteria.py                  (nuevo)
scripts/process_cowrie_ndjson.py                       (integración alerts)
pipeline/Dockerfile                                    (COPY pipeline/alerts)
backend/app/domain/analytics.py                        (AlertItem)
backend/app/domain/ports/analytics_repository.py       (list_alerts protocol)
backend/app/adapters/persistence/analytics_repository.py (list_alerts impl)
backend/app/application/analytics_service.py           (list_alerts service)
backend/app/api/schemas.py                             (AlertItemResponse, AlertPageResponse)
backend/app/api/v1/alerts.py                          (nuevo router)
backend/app/api/v1/router.py                           (include alerts_router)
backend/tests/unit/test_alerts_service.py              (nuevo)
backend/tests/integration/test_alerts_api.py           (nuevo)
```

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| Criterios de alerta (pipeline) | test_alert_criteria.py | Unit | ✅ 20/20 | ✅ Módulo no existía | ✅ 9/9 | ✅ 9 casos (high, critical, low, medium, login, download, vacío, múltiple, contexto) | ✅ Limpio |
| Servicio de alertas (backend) | test_alerts_service.py | Unit | ✅ 12/12 | ✅ Módulo no existía | ✅ 5/5 | ✅ 5 casos (vacío, resultados, filtro status, filtro session, paginación) | ✅ Limpio |
| Endpoint REST (backend) | test_alerts_api.py | Integration | ✅ 12/12 | ✅ 401 sin auth | ✅ 4/4 | ✅ auth + paginación + filtro | ✅ Limpio |

## Validación

```text
pruebas pipeline:    29/29
pruebas backend:     30/30
validación LAB:      superada con 10 servicios persistentes
migración 0009:      aplicada y verificada en PostgreSQL
```

Verificación de la tabla alerts:

```sql
-- Columnas y constraints actuales
id              UUID PK (gen_random_uuid)
session_key     TEXT NOT NULL FK → sessions ON DELETE CASCADE
event_hash      TEXT FK → eventos ON DELETE SET NULL
pipeline_run_id INTEGER FK → pipeline_runs ON DELETE SET NULL
trigger         TEXT NOT NULL  CHECK: high_risk | successful_login | file_download
channel         TEXT NOT NULL DEFAULT 'telegram'  CHECK: telegram | log | webhook
status          TEXT NOT NULL DEFAULT 'pending'  CHECK: pending | sent | failed | suppressed
risk_level      TEXT
risk_score      INTEGER  CHECK: 0–100
event_timestamp TIMESTAMP WITH TZ
triggered_at    TIMESTAMP WITH TZ NOT NULL DEFAULT NOW()
sent_at         TIMESTAMP WITH TZ
mttd_seconds    NUMERIC
error_code      TEXT
error_detail    TEXT
UNIQUE(session_key, trigger)
```

Verificación end-to-end:

```text
pipeline run (recovery) → 105 eventos → 12 alertas generadas
GET /api/v1/alerts → 200, total: 12
primera alerta:
  trigger: successful_login
  channel: telegram
  status:  pending
  risk_level: medium
  risk_score: 25
```

Validación de los 10 servicios LAB:

```text
oscorp_cowrie            Up (healthy)
oscorp_attacker_sim      Up
oscorp_postgres          Up (healthy)
oscorp_elasticsearch     Up (healthy)
oscorp_kibana            Up (healthy)
oscorp_n8n               Up (healthy)
oscorp_pipeline_worker   Up (healthy)
oscorp_payload_server    Up
oscorp_backend           Up (healthy)
oscorp_frontend          Up (healthy)
```

La Fase 23 queda completa. El siguiente trabajo corresponde a la Fase 24:
notificaciones Telegram.
