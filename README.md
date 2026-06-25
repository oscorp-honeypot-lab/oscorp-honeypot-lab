# oscorp-honeypot-lab

Laboratorio OSCORP refactorizado para ejecutar un honeypot SSH con dos modos:

- `lab`: entorno local reproducible con Cowrie, attacker-sim, n8n, PostgreSQL, Elasticsearch y Kibana.
- `real`: entorno preparado para procesar logs de una VPS externa sin levantar Cowrie local.

## Requisitos

- Docker Desktop
- PowerShell

## Levantar modo LAB

```powershell
.\scripts\setup.ps1
```

El script crea `.env` cuando falta, configura la clave de cifrado de n8n,
sincroniza credenciales y workflow, y levanta los servicios.

Después de la primera configuración también puede utilizarse:

```powershell
docker compose --profile lab up -d
```

Servicios principales:

```text
Cowrie:        localhost:2222
n8n:           http://localhost:5678
PostgreSQL:    localhost:5433
Elasticsearch: http://localhost:9200
Kibana:        http://localhost:5601
Backend API:   http://localhost:8000/docs
Frontend:      http://localhost:5173
pipeline-worker: interno, sin puerto publicado
```

La interfaz inicial permite iniciar sesión y consultar el resumen operativo,
la evolución temporal y la distribución del Attack Risk Score.

El setup genera una contraseña administrativa aleatoria en el `.env` local:

```text
OSCORP_API_ADMIN_USERNAME
OSCORP_API_ADMIN_PASSWORD
```

La API usa sesiones de servidor mediante cookies; no entrega tokens para
guardar en `localStorage`.

Endpoints disponibles:

```text
POST /api/v1/auth/login
GET  /api/v1/auth/me
POST /api/v1/auth/logout
POST /api/v1/users
GET  /api/v1/analytics/summary
GET  /api/v1/sessions
GET  /api/v1/sessions/{session_key}
PATCH /api/v1/sessions/{session_key}/review
GET  /api/v1/events
GET  /api/v1/exports/sessions.csv
GET  /api/v1/exports/events.csv
```

Las lecturas analíticas requieren una sesión autenticada. Los listados usan
`page` y `page_size` con un máximo de 100 elementos, y no exponen contraseñas
ni el evento crudo almacenado.

Sesiones y eventos aceptan filtros combinables por `from`, `to`, `src_ip`,
`country`, `username` y `event_type`. Las sesiones también permiten
`risk_level` y `reviewed`. Marcar una sesión como revisada requiere rol
`analyst` o `admin` y token CSRF.

Las exportaciones CSV reutilizan los mismos filtros, permiten `page` y
`page_size` hasta 1000 filas por archivo, e informan el total disponible en
cabeceras `X-Export-*`. Se generan como UTF-8 con BOM y no incluyen
contraseñas ni eventos crudos.

## Generar eventos de ataque

```powershell
docker compose --profile lab run --rm attacker-sim ./run_scenario.sh full
```

Escenarios disponibles:

```powershell
docker compose --profile lab run --rm attacker-sim ./run_scenario.sh brute-force
docker compose --profile lab run --rm attacker-sim ./run_scenario.sh recon
docker compose --profile lab run --rm attacker-sim ./run_scenario.sh malware-download
docker compose --profile lab run --rm attacker-sim ./run_scenario.sh full
```

## Procesar cowrie.json

```powershell
.\scripts\run_pipeline.ps1
```

Este comando queda como mecanismo de recuperación manual. La ejecución normal
del flujo completo se realiza desde n8n:

```powershell
.\scripts\run_n8n_pipeline.ps1
```

El pipeline lee:

```text
cowrie/logs/cowrie.json
```

Y escribe en:

```text
PostgreSQL: tabla eventos
Elasticsearch: indice cowrie-events
```

La ejecución normal usa un checkpoint persistente en PostgreSQL y procesa
solo líneas nuevas. `run_pipeline.ps1` mantiene la recuperación completa sin
alterar ese checkpoint.

## Demo y validación

```powershell
.\scripts\validate_lab.ps1
.\scripts\validate_n8n_contract.ps1
.\scripts\run_demo.ps1
.\scripts\smoke_test.ps1
.\scripts\recalculate_risk_scores.ps1
```

El smoke test comprueba servicios, ataque completo, descarga offline,
orquestación desde n8n, persistencia, indexación e idempotencia.

## Administración

```powershell
.\scripts\backup.ps1
.\scripts\reset_lab.ps1
```

## Artefactos importantes

```text
docker-compose.yml
.env.example
pipeline/migrations/
attacker-sim/
scripts/process_cowrie_ndjson.py
scripts/run_pipeline.ps1
scripts/setup.ps1
scripts/validate_lab.ps1
scripts/validate_n8n_contract.ps1
scripts/validate_checkpoint.ps1
scripts/validate_traceability.ps1
scripts/validate_partial_errors.ps1
scripts/validate_failure_recovery.ps1
scripts/validate_sessions.ps1
scripts/run_demo.ps1
scripts/run_n8n_pipeline.ps1
scripts/smoke_test.ps1
scripts/recalculate_risk_scores.ps1
scripts/validate_risk_scores.ps1
n8n/workflows/oscorp-workflow.json
pipeline/contracts/
backend/
docs/evidencias/
ESTADO_Y_ROADMAP.md
```

## Notas

- `.env` queda fuera de git.
- `n8n` está fijado por defecto en la versión `2.15.0`.
- `event_hash` es el identificador idempotente de eventos. No se usa `event_uuid` como único porque Cowrie puede repetirlo en varios eventos.
- El pipeline y las migraciones se ejecutan dentro de Docker; no requieren Python instalado en el host.
- La simulación de descargas usa payloads inocuos servidos dentro de la red LAB.
