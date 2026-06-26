# Fase 31 - Formatos y entrega de reportes

Fecha: 26 de junio de 2026.

## Alcance

```text
[x] Descarga de reportes HTML y CSV desde la API.
[x] Descarga desde la aplicacion web mediante controles en el dashboard.
[x] Envio por Telegram desde la API con CSRF.
[x] Registro de descargas, envios, skips y errores en report_deliveries.
[x] Validacion de contrato OpenAPI, backend, pipeline y frontend.
```

## Skills

```text
buscados:
- report delivery html pdf csv telegram backend api security testing

utilizados:
- python-expert-best-practices-code-review
- n8n-credentials-and-security
- n8n-error-handling
- pdf revisado, pero no usado para implementacion final

instalados: ninguno

descartados:
- skills externos de PDF/report delivery con baja instalacion o fuera del stack.
- PDF en esta fase: el objetivo pide HTML o PDF y CSV; HTML reduce dependencias
  y mantiene la entrega reproducible. PDF queda como mejora futura.
```

## Implementacion

```text
Persistencia:
  migration 0014_report_deliveries
  report_deliveries:
    report_run_id, user_id, channel, format, status, filename,
    error_code, error_detail, started_at, finished_at

Backend:
  GET  /api/v1/reports/latest/{period_type}
  GET  /api/v1/reports/latest/{period_type}/download?format=html|csv
  POST /api/v1/reports/latest/{period_type}/telegram?format=html|csv

Formatos:
  HTML: reporte tabular autocontenido y descargable.
  CSV: UTF-8 BOM con proteccion contra formula injection.

Telegram:
  usa OSCORP_API_TELEGRAM_BOT_TOKEN y OSCORP_API_TELEGRAM_CHAT_ID.
  docker-compose mapea estas variables desde TELEGRAM_BOT_TOKEN/CHAT_ID.
  si no hay credenciales: status=skipped, error_code=telegram_not_configured.

Frontend:
  panel "Entregas reproducibles" en Dashboard.
  controles por periodo daily/weekly:
    - descargar HTML
    - descargar CSV
    - enviar Telegram
```

## Archivos creados o modificados

```text
pipeline/migrations/versions/0014_report_deliveries.py
backend/app/application/report_service.py
backend/app/api/v1/reports.py
backend/app/infrastructure/telegram.py
backend/app/domain/analytics.py
backend/app/domain/ports/analytics_repository.py
backend/app/adapters/persistence/analytics_repository.py
backend/app/api/dependencies.py
backend/app/api/v1/router.py
backend/app/api/schemas.py
backend/app/infrastructure/config.py
backend/app/main.py
backend/tests/unit/test_report_service.py
backend/tests/integration/test_reports_api.py
backend/tests/contract/test_openapi.py
frontend/src/api/client.ts
frontend/src/features/dashboard/DashboardPage.tsx
frontend/src/features/sessions/SessionDetailPage.tsx
frontend/src/styles/global.css
docker-compose.yml
ESTADO_Y_ROADMAP.md
docs/evidencias/fase31_formatos_entrega_reportes.md
```

## Validacion

```text
docker compose run --rm backend pytest -q -p no:cacheprovider
resultado: 57/57 OK

docker compose run --rm --no-deps migrate python -m unittest discover -s /app/tests
resultado: 133/133 OK

npm run build
resultado: OK

npm.cmd run test
resultado: 12/12 OK

docker compose --profile lab run --rm migrate
resultado: Alembic upgrade hasta 0014_report_deliveries OK

SELECT version_num FROM alembic_version;
resultado: 0014_report_deliveries
```

Validacion visual:

```text
Dashboard cargado en http://localhost:5173.
Panel "Entregas reproducibles" visible.
Consola del navegador: 0 errores.
Botones HTML/CSV/Telegram por periodo con dimensiones estables 38x38.
```

## Resultado

```text
La Fase 31 queda implementada y validada en LAB.
La entrega por Telegram queda segura: sin credenciales configuradas no intenta
exponer secretos en workflow ni frontend; registra skipped en base de datos.
```
