# Fase 36 — Separación LAB / REAL: campo `source_mode`

**Fecha:** 2026-06-27
**Estado:** Completada

## Objetivo

Agregar un campo `source_mode` (`'lab'` | `'real'`) a los eventos y sesiones para distinguir el origen de los datos: generados en el entorno LAB local (Cowrie + attacker-sim) vs. capturados en producción REAL (VPS expuesta a internet).

## Cambios implementados

### 1. Migración de base de datos (`0016_source_mode`)

- Columna `source_mode TEXT NOT NULL DEFAULT 'lab'` en `eventos` y `sessions`
- Constraint CHECK: `source_mode IN ('lab', 'real')`
- Índice en `sessions.source_mode` para filtrado eficiente
- Backfill automático: todos los registros existentes quedan como `'lab'`

### 2. Pipeline de ingestión (`scripts/process_cowrie_ndjson.py`)

- `INSERT_EVENT_SQL`: agrega `source_mode` a la inserción de eventos
- `SESSION_UPSERT_SQL`: deriva `source_mode` de los eventos via `MIN(e.source_mode)` en el CTE agregado; NO se sobreescribe en conflicto (inmutable una vez seteado)
- `insert_events(connection, events, source_mode="lab")`: nuevo parámetro
- `execute_pipeline(..., source_mode="lab")`: nuevo parámetro con validación

### 3. Pipeline worker (`pipeline/pipeline_worker.py`)

- `validate_request()`: acepta campo opcional `source_mode` (default: `'lab'`), rechaza valores distintos de `'lab'` o `'real'`
- `execute_pipeline()`: recibe y propaga `source_mode`

### 4. Backend

| Capa | Cambio |
|------|--------|
| `app/domain/analytics.py` | `source_mode: str` en `SessionListItem`; `source_mode: str \| None` en `SessionFilters` |
| `app/adapters/persistence/analytics_repository.py` | `s.source_mode` en `SESSION_SELECT`; filter en `_session_filter_sql` |
| `app/api/schemas.py` | `source_mode: str` en `SessionListItemResponse` |
| `app/api/v1/analytics.py` | Query param `source_mode` con validación regex `^(lab\|real)$` |

### 5. Frontend

- `types.gen.ts`: `source_mode: string` en `SessionListItemResponse` y en `SessionsApiV1SessionsGetData`
- `client.ts`: `sourceMode?: string` en `SessionQuery` y `getSessions()`
- `SessionsPage.tsx`: columna "Modo" con badge LAB/REAL + filtro select
- `SessionDetailPage.tsx`: badge de modo en el header de detalle
- `global.css`: clases `.source-mode-lab` (azul) y `.source-mode-real` (naranja)

## Pruebas ejecutadas

### Pipeline — Unit Tests (TDD)

```
pipeline/tests/test_pipeline_worker.py — 6/6 PASS
  ✓ source_mode lab aceptado
  ✓ source_mode real aceptado
  ✓ source_mode omitido → default 'lab'
  ✓ source_mode inválido → error
  ✓ string vacío rechazado
  ✓ campo desconocido rechazado aunque source_mode sea válido
```

### Backend — Integration Tests

```
tests/integration/test_analytics_api.py — 12/12 PASS
  ✓ test_source_mode_field_in_session_response
  ✓ test_source_mode_filter_lab_returns_matching_sessions
  ✓ test_source_mode_filter_real_returns_empty
  ✓ test_source_mode_invalid_value_returns_422
  + 8 tests previos sin regresiones
```

### Suite completa

77 tests pasan. Los 3 errores en `test_reports_api.py` son pre-existentes (conflicto de constraint `uq_report_runs_period` por el lab corriendo en paralelo).

### TypeScript

```
npx tsc --noEmit → sin errores
```

## Flujo de uso

### Modo LAB (por defecto)
El pipeline n8n llama al worker sin `source_mode` → default `'lab'`. Todos los eventos del attacker-sim local se marcan como LAB.

### Modo REAL
Después de sincronizar logs del VPS con `sync_vps_logs.ps1 -RunPipeline`, el script llama al pipeline con `source_mode=real`. Los eventos del VPS se marcan como REAL.

### Filtrado en UI
La página de sesiones tiene un filtro "Modo" (LAB | REAL | Todos). El badge azul indica LAB, naranja indica REAL.

## Invariante de diseño

`source_mode` es inmutable una vez seteado. En el `ON CONFLICT DO UPDATE` de la upsert de sesiones, no se incluye en el `SET` clause. Esto garantiza que si una sesión fue capturada como REAL, siempre conserva ese origen aunque el pipeline se re-ejecute.
