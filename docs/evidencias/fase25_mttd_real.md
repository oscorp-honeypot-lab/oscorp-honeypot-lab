# Fase 25 — Medición real de MTTD

Fecha: 25 de junio de 2026.

## Alcance

```text
[x] MttdTriggerStat y MttdStats en domain/analytics.py
[x] get_mttd_stats() en Protocol AnalyticsRepository
[x] Implementación SQL en adapters/persistence/analytics_repository.py
    — AVG, MIN, MAX, PERCENTILE_CONT(0.95) sobre mttd_seconds de alertas enviadas
    — COUNT FILTER por status para total_sent, total_failed, total_pending
    — failure_rate = total_failed / (total_sent + total_failed)
    — breakdown por trigger con GROUP BY
[x] get_mttd_stats() en AnalyticsService
[x] MttdTriggerStatResponse y MttdStatsResponse en api/schemas.py
[x] GET /api/v1/analytics/mttd — autenticación requerida (Role.VIEWER)
[x] getMttdStats() en frontend/src/api/client.ts
[x] SDK regenerado desde el backend con openapi-ts (mttdStatsApiV1AnalyticsMttdGet)
[x] Panel MttdPanel en DashboardPage.tsx:
    — 6 métricas: promedio, mínimo, máximo, p95, enviadas, tasa de fallo
    — tabla de breakdown por tipo de evento (alto riesgo, login, descarga)
    — estado vacío si no hay alertas enviadas
[x] Estilos .mttd-panel, .mttd-stats-grid, .mttd-stat, .mttd-trigger-table en global.css
[x] 4 tests unit + 4 integration backend = 8 nuevos → 38 backend totales
[x] Pipeline: 61/61 sin cambios
[x] TypeScript limpio (tsc --noEmit sin errores)
```

## Skills

```text
buscados: PostgreSQL PERCENTILE_CONT, FILTER aggregate, openapi-ts regeneration

utilizados:
- PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY mttd_seconds) — función ordered-set
- COUNT(*) FILTER (WHERE status = 'sent') — aggregate filter (PostgreSQL 9.4+)
- openapi-ts en el container con URL interna http://backend:8000/openapi.json

instalados: ninguno (todos existentes)
```

## Implementación

```text
SQL (dos queries en get_mttd_stats):

1. Query global:
   SELECT AVG(mttd_seconds), MIN(mttd_seconds), MAX(mttd_seconds),
          PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY mttd_seconds),
          COUNT(*) FILTER (WHERE status='sent'),
          COUNT(*) FILTER (WHERE status='failed'),
          COUNT(*) FILTER (WHERE status='pending')
   FROM alerts

   — El AVG/MIN/MAX/PERCENTILE_CONT no necesita WHERE status='sent'
     porque mttd_seconds es NULL para alertas no enviadas

2. Query por trigger:
   SELECT trigger, AVG(mttd_seconds), MIN(mttd_seconds),
          MAX(mttd_seconds), COUNT(*)
   FROM alerts
   WHERE status='sent' AND mttd_seconds IS NOT NULL
   GROUP BY trigger ORDER BY trigger

failure_rate = round(total_failed / (total_sent + total_failed), 4) — 0.0 si ambos cero

API:
  GET /api/v1/analytics/mttd → 200 MttdStatsResponse (requiere autenticación VIEWER)
  No tiene parámetros — devuelve siempre el estado global

Frontend:
  getMttdStats() → useQuery → MttdPanel
  fmt(seconds) → "15s" | "21m" | "4.0h" — formato legible humano
  TRIGGER_LABELS: mapeo de clave a etiqueta en español
  mttd-stat--warning: clase CSS para tasa de fallo (ámbar)
  Panel se oculta si mttd.data es undefined (carga o error silencioso)
```

Archivos creados o modificados:

```text
backend/app/domain/analytics.py                              (MttdTriggerStat + MttdStats)
backend/app/domain/ports/analytics_repository.py             (get_mttd_stats en Protocol)
backend/app/adapters/persistence/analytics_repository.py     (implementación SQL)
backend/app/application/analytics_service.py                 (delegación)
backend/app/api/schemas.py                                   (MttdTriggerStatResponse + MttdStatsResponse)
backend/app/api/v1/analytics.py                              (GET /analytics/mttd)
backend/tests/unit/test_mttd_service.py                      (nuevo — 4 tests)
backend/tests/integration/test_mttd_api.py                   (nuevo — 4 tests)
frontend/src/api/client.ts                                   (getMttdStats)
frontend/src/api/generated/sdk.gen.ts                        (regenerado)
frontend/src/api/generated/types.gen.ts                      (regenerado)
frontend/src/features/dashboard/DashboardPage.tsx            (MttdPanel)
frontend/src/styles/global.css                               (estilos MTTD)
```

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| get_mttd_stats() | test_mttd_service.py | Unit | ✅ 30/30 | ✅ ImportError | ✅ 4/4 | ✅ vacío + valores + failure_rate + by_trigger | ✅ Limpio |
| GET /analytics/mttd | test_mttd_api.py | Integration | ✅ 30/30 | ✅ 404 | ✅ 4/4 | ✅ 401 + 200 + tipos + by_trigger | ✅ Limpio |

## Validación

```text
pruebas backend:     38/38  (8 nuevas + 30 regresión)
pruebas pipeline:    61/61  (sin cambios)
TypeScript:          0 errores (tsc --noEmit)
validación LAB:      10 servicios healthy
```

Respuesta real del endpoint GET /api/v1/analytics/mttd:

```json
{
  "avg_seconds": 1270.997916673913,
  "min_seconds": 15.617568,
  "max_seconds": 14461.400576,
  "p95_seconds": 4212.08000475,
  "total_sent": 46,
  "total_failed": 1,
  "total_pending": 0,
  "failure_rate": 0.0213,
  "by_trigger": [
    {
      "trigger": "file_download",
      "avg_seconds": 1084.2112115,
      "min_seconds": 15.875129,
      "max_seconds": 4193.19307,
      "count": 4
    },
    {
      "trigger": "successful_login",
      "avg_seconds": 1288.7871266904763,
      "min_seconds": 15.617568,
      "max_seconds": 14461.400576,
      "count": 42
    }
  ]
}
```

Interpretación:
- MTTD promedio: ~21 minutos
- MTTD mínimo: ~16 segundos (pipeline corrió casi inmediatamente)
- MTTD máximo: ~4 horas (alerta generada de sesión antigua)
- Percentil 95: ~70 minutos
- Tasa de fallo: 2.13% (1 alerta con http_429)
- Login exitoso domina con 42/46 alertas (91%)
