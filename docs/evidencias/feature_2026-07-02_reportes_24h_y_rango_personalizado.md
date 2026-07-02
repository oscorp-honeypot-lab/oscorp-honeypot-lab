# Feature — Reporte "últimas 24h" (rolling) y descarga con rango de fechas personalizado

Fecha: 2 de julio de 2026

## Objetivo

El reporte diario existente solo cubre 00:00–23:59 UTC del día anterior (`pipeline/reports/engine.py
closed_report_periods()`, precalculado por un cron/scheduler en la tabla `report_runs`), por lo que
los eventos del día en curso no aparecen en ningún reporte hasta que corre el cron del día
siguiente. Se agregó:

1. Un reporte "últimas 24h" — ventana rolling de 24 horas calculada en el momento del pedido,
   expuesto en `GET /api/v1/reports/latest/24h` (y su descarga en
   `GET /api/v1/reports/latest/24h/download`) y en el dashboard.
2. Descarga de reporte con rango de fechas arbitrario:
   `GET /api/v1/reports/custom/download?start=...&end=...&format=html|csv`, con un formulario en el
   dashboard.

## Decisión de diseño: sin persistencia para reportes ad-hoc

A diferencia de `daily`/`weekly` (que se precalculan una vez por período y quedan auditados en
`report_runs`/`report_deliveries`), los reportes `24h` y `custom` se calculan **en vivo, en cada
pedido, sin persistir nada**. Motivo: la ventana de "últimas 24h" es siempre distinta según el
momento del pedido — cachear "el último" no tiene sentido — y esto evita una migración para relajar
el `CHECK (period_type IN ('daily', 'weekly'))` de `report_runs` y el FK `NOT NULL` de
`report_deliveries.report_run_id`. Decisión confirmada explícitamente con el usuario antes de
implementar. Contrapartida aceptada: no queda registro de auditoría (quién descargó qué y cuándo)
para estos dos tipos de reporte, a diferencia de `daily`/`weekly`.

## Implementación

### Backend

- `AnalyticsRepository.build_report_dataset(start, end, rules_version, limit=20)` — nuevo método
  (puerto en `app/domain/ports/analytics_repository.py`, implementación async en
  `app/adapters/persistence/analytics_repository.py`) que porta las 9 consultas de
  `pipeline/reports/engine.py.build_report_dataset()` (totales, top IPs/países/credenciales/
  comandos, descargas, hashes maliciosos, sesiones críticas, MTTD, alertas fallidas) al estilo async
  SQLAlchemy (`session.execute(text(...), params)`) ya usado en el resto del repositorio, en vez de
  las consultas sync con `psycopg.Connection` que usa el motor offline del pipeline. Duplicación de
  SQL conocida y aceptada: el pipeline corre sync/offline desde un scheduler; el backend es async y
  no comparte capa de acceso a datos con él hoy.
- `ReportService` (`app/application/report_service.py`):
  - `latest(period_type="24h")` calcula `end = now(UTC)`, `start = end - 24h`, arma un `ReportRun` en
    memoria (id sintético `uuid4()`, no persistido) con el dataset del repositorio.
  - `custom_range(start, end)` — nuevo método, valida `start < end` y rango ≤ 90 días
    (`MAX_CUSTOM_RANGE_DAYS`), levanta `ReportPeriodInvalid` si no.
  - `download_latest()`/nuevo `download_custom_range()` — para períodos ad-hoc (`_is_adhoc`) saltean
    `start_report_delivery`/`finish_report_delivery` por completo (evita el `FOREIGN KEY` inválido
    que resultaría de referenciar un `report_runs.id` sintético inexistente).
  - `send_latest_telegram()` — rechaza explícitamente `period_type` ad-hoc con `ReportPeriodInvalid`
    (guarda defensiva: la ruta genérica `/latest/{period_type}/telegram` también matchea `24h`, y sin
    este guard un POST directo a la API rompería contra el mismo FK).
- `app/api/v1/reports.py` — sin cambios en las rutas `/latest/{period_type}` (`period_type="24h"` ya
  fluye transparentemente); nueva ruta `GET /custom/download` con query params `start`/`end`
  (`datetime`) y `format`; `ReportPeriodInvalid` mapeado a 400 en los tres endpoints relevantes.
- `app/main.py` — `ReportService` recibe `rules_version="1.1.0"` explícito (antes implícito vía el
  valor por defecto del constructor), igual que `AnalyticsService`/`ExportService`.

### Frontend

- `frontend/src/api/client.ts` — `ReportPeriodType` ahora incluye `"24h"`; nuevo
  `downloadCustomReport(start, end, format)`; se extrajo `triggerReportDownload()` compartido entre
  `downloadLatestReport`/`downloadCustomReport` (antes duplicado).
- `frontend/src/features/dashboard/DashboardPage.tsx` — `ReportPanel` agrega la fila "Últimas 24h"
  (sin botón de Telegram, ya que el backend lo rechaza) y un formulario "Rango personalizado" con dos
  `<input type="datetime-local">` y botones de descarga HTML/CSV, deshabilitados hasta que
  `start < end`. Sigue el patrón imperativo `async`/`useState` (`reportBusy`/`reportStatus`) ya
  usado en el panel, sin introducir React Query para esto.
- `frontend/src/styles/global.css` — estilos para `.report-custom-range` consistentes con
  `.report-action-row` existente.

## Verificación (TDD)

### `backend/tests/unit/test_report_service.py`

Ciclo RED → GREEN → TRIANGULATE en 8 tests nuevos sobre un fake `_Repo` extendido con
`build_report_dataset`:

| Test | Cubre |
|---|---|
| `test_latest_rolling_24h_computes_window_from_now` | ventana de 24h calculada desde `now()` |
| `test_download_latest_24h_skips_delivery_tracking` | no llama a `start_report_delivery`/`finish_report_delivery` |
| `test_custom_range_happy_path` | dataset correcto para rango válido |
| `test_custom_range_rejects_start_after_end` | `ReportPeriodInvalid` |
| `test_custom_range_rejects_equal_start_and_end` | `ReportPeriodInvalid` (triangulación) |
| `test_custom_range_rejects_range_over_max_days` | `ReportPeriodInvalid` por rango > 90 días |
| `test_download_custom_range_skips_delivery_tracking` | sin persistencia, filename contiene "custom" |
| `test_send_latest_telegram_rejects_adhoc_period` | guarda de Telegram para `24h` |

18/18 tests unitarios de `test_report_service.py` ✅ (10 preexistentes + 8 nuevos). Suite completa de
unit tests del backend: 49/49 ✅.

### `backend/tests/integration/test_reports_api.py`

5 tests nuevos contra Postgres real (`TestClient(app)` + DB de desarrollo):
`test_latest_report_24h_computes_live_rolling_window`,
`test_download_latest_report_24h_does_not_persist_delivery` (verifica
`SELECT COUNT(*) FROM report_runs WHERE period_type = '24h'` → 0),
`test_send_latest_report_24h_telegram_rejected` (400), `test_download_custom_report_range`,
`test_download_custom_report_rejects_start_after_end` (400). 8/8 tests de
`test_reports_api.py` ✅ (3 preexistentes + 5 nuevos).

Nota de entorno: en Windows, `psycopg` async requiere `WindowsSelectorEventLoopPolicy` (el
`ProactorEventLoop` por defecto no es compatible) — limitación preexistente del entorno local, no
relacionada con este cambio; confirmada porque el test preexistente
`test_latest_report_downloads_html_and_csv` fallaba igual antes de tocar código nuevo. No se
modificó el repositorio para "arreglar" esto (CI corre en Linux, donde no aplica).

### Verificación end-to-end

- `curl` directo contra `GET /api/v1/reports/latest/24h` con el backend real (datos reales del
  honeypot): devolvió `period_type: "24h"`, ventana de 86400s, 2418 eventos/506 sesiones de las
  últimas 24h reales.
- `GET /api/v1/reports/custom/download?start=2026-06-01...&end=2026-06-30...&format=csv`: 200,
  CSV con `period_type,custom` y datos reales del rango.
- `SELECT period_type, COUNT(*) FROM report_runs GROUP BY period_type` tras múltiples descargas
  24h/custom: solo `daily`/`weekly`, cero filas `24h`/`custom` — confirma la decisión de "sin
  persistencia".
- Verificación visual con Chrome headless (Puppeteer + CDP) contra el dashboard real
  (`localhost:5173`): fila "Últimas 24h" visible con solo 2 botones (HTML/CSV, sin Telegram);
  formulario "Rango personalizado" visible y funcional; clic en ambos disparó
  `GET /api/v1/reports/latest/24h/download` y `GET /api/v1/reports/custom/download` → 200, mensaje
  "Descarga preparada", sin errores de consola nuevos.

## Archivos modificados

| Archivo | Acción |
|---|---|
| `backend/app/domain/ports/analytics_repository.py` | Modificado — `build_report_dataset` en el Protocol |
| `backend/app/adapters/persistence/analytics_repository.py` | Modificado — implementación async de `build_report_dataset` |
| `backend/app/application/report_service.py` | Modificado — `ReportPeriodInvalid`, `latest()`, `custom_range()`, `download_latest()`, `download_custom_range()`, guarda en `send_latest_telegram()` |
| `backend/app/api/v1/reports.py` | Modificado — manejo de `ReportPeriodInvalid`, ruta nueva `GET /custom/download` |
| `backend/app/main.py` | Modificado — `rules_version` explícito en `ReportService` |
| `backend/tests/unit/test_report_service.py` | Modificado — 8 tests nuevos |
| `backend/tests/integration/test_reports_api.py` | Modificado — 5 tests nuevos |
| `frontend/src/api/client.ts` | Modificado — `ReportPeriodType`, `downloadCustomReport`, `triggerReportDownload` compartido |
| `frontend/src/features/dashboard/DashboardPage.tsx` | Modificado — fila "Últimas 24h" y formulario de rango personalizado en `ReportPanel` |
| `frontend/src/styles/global.css` | Modificado — estilos `.report-custom-range` |
