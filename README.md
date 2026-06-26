# oscorp-honeypot-lab

Laboratorio OSCORP para ejecutar un honeypot SSH con dos modos:

- `lab`: entorno local reproducible con Cowrie, attacker-sim, n8n, PostgreSQL, Elasticsearch y Kibana.
- `real`: entorno preparado para procesar logs de una VPS externa sin levantar Cowrie local.

## Requisitos

- Docker Desktop
- PowerShell
- Node.js y Python solo si se quiere levantar backend/frontend fuera de Docker

## Levantar la aplicacion

Hay dos formas habituales de usar el laboratorio.

### Opcion A: LAB completo con Docker

```powershell
.\scripts\setup.ps1
```

El script crea `.env` cuando falta, configura la clave de cifrado de n8n,
sincroniza credenciales y workflow, y levanta los servicios.

Despues de la primera configuracion tambien puede utilizarse:

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

El setup genera una contrasena administrativa aleatoria en el `.env` local:

```text
OSCORP_API_ADMIN_USERNAME
OSCORP_API_ADMIN_PASSWORD
```

La app web queda disponible en:

```text
http://localhost:5173/dashboard
```

Dashboard operativo de Kibana:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\configure_kibana_phase32.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate_kibana_phase32.ps1
```

```text
http://localhost:5601/app/dashboards#/view/oscorp-phase32-operational
```

### Opcion B: backend/frontend manuales

Esta opcion es util para desarrollar la app web desde terminal. La base de
datos, Elasticsearch, Cowrie, n8n y servicios auxiliares siguen corriendo en
Docker; solo se levantan backend y frontend localmente.

Primero levantar la infraestructura sin backend/frontend:

```powershell
docker compose --profile lab up -d postgres elasticsearch kibana n8n cowrie payload-server attacker-sim pipeline-worker
```

Backend:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

Get-Content ..\.env | Where-Object { $_ -match '^[A-Za-z_][A-Za-z0-9_]*=' } | ForEach-Object {
  $name, $value = $_ -split '=', 2
  Set-Item -Path "Env:$name" -Value $value
}

$env:OSCORP_API_DATABASE_URL = "postgresql+psycopg://$($env:POSTGRES_USER):$($env:POSTGRES_PASSWORD)@localhost:$($env:POSTGRES_PORT)/$($env:POSTGRES_DB)"

.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend, en otra terminal:

```powershell
cd frontend
npm install
npm run dev
```

Si el backend o frontend de Docker ya estan ocupando los puertos, detenerlos:

```powershell
docker compose stop backend frontend
```

## Generar ataques simulados

Los ataques simulados se ejecutan desde el contenedor `attacker-sim` contra
Cowrie. Son escenarios controlados e inocuos: generan logs de autenticacion,
comandos y descargas simuladas dentro del LAB.

Antes de ejecutar ataques, el LAB debe estar levantado y Cowrie saludable:

```powershell
docker compose ps cowrie attacker-sim payload-server
```

Ejecutar una campana completa:

```powershell
docker compose --profile lab run --rm attacker-sim ./run_scenario.sh full
```

Escenarios disponibles:

```powershell
# Fuerza bruta controlada contra SSH/Cowrie.
docker compose --profile lab run --rm attacker-sim ./run_scenario.sh brute-force

# Reconocimiento post-login: whoami, id, uname, ps, netstat, etc.
docker compose --profile lab run --rm attacker-sim ./run_scenario.sh recon

# Descarga simulada de payloads inocuos desde payload-server.
docker compose --profile lab run --rm attacker-sim ./run_scenario.sh malware-download

# Secuencia completa: brute-force + recon + malware-download.
docker compose --profile lab run --rm attacker-sim ./run_scenario.sh full
```

El ataque escribe eventos nuevos en:

```text
cowrie/logs/cowrie.json
```

Eventos esperados:

```text
cowrie.login.failed
cowrie.login.success
cowrie.command.input
cowrie.session.file_download
```

Despues de generar el ataque, procesar los logs para que aparezcan en la API,
dashboard, PostgreSQL y Elasticsearch:

```powershell
.\scripts\run_n8n_pipeline.ps1
```

Tambien puede ejecutarse el flujo completo de demo, que valida LAB, genera el
ataque `full`, procesa por n8n y comprueba que no se dupliquen eventos:

```powershell
.\scripts\run_demo.ps1
```

Verificaciones rapidas:

```powershell
(Get-Content cowrie\logs\cowrie.json).Count
docker compose exec postgres psql -U oscorp -d oscorp -c "SELECT COUNT(*) FROM eventos;"
Invoke-RestMethod -Uri http://localhost:9200/cowrie-events/_count
```

## Procesar cowrie.json

```powershell
.\scripts\run_pipeline.ps1
```

Este comando queda como mecanismo de recuperacion manual. La ejecucion normal
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

La ejecucion normal usa un checkpoint persistente en PostgreSQL y procesa solo
lineas nuevas. `run_pipeline.ps1` mantiene la recuperacion completa sin alterar
ese checkpoint.

## API y dashboard

La API usa sesiones de servidor mediante cookies; no entrega tokens para
guardar en `localStorage`.

Endpoints principales:

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

Las lecturas analiticas requieren una sesion autenticada. Los listados usan
`page` y `page_size` con un maximo de 100 elementos, y no exponen contrasenas
ni el evento crudo almacenado.

Sesiones y eventos aceptan filtros combinables por `from`, `to`, `src_ip`,
`country`, `username` y `event_type`. Las sesiones tambien permiten
`risk_level` y `reviewed`. Marcar una sesion como revisada requiere rol
`analyst` o `admin` y token CSRF.

Las exportaciones CSV reutilizan los mismos filtros, permiten `page` y
`page_size` hasta 1000 filas por archivo, e informan el total disponible en
cabeceras `X-Export-*`. Se generan como UTF-8 con BOM y no incluyen contrasenas
ni eventos crudos.

## Demo y validacion

```powershell
.\scripts\validate_lab.ps1
.\scripts\validate_n8n_contract.ps1
.\scripts\run_demo.ps1
.\scripts\smoke_test.ps1
.\scripts\recalculate_risk_scores.ps1
```

El smoke test comprueba servicios, ataque completo, descarga offline,
orquestacion desde n8n, persistencia, indexacion e idempotencia.

## Administracion

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
- `n8n` esta fijado por defecto en la version `2.15.0`.
- `event_hash` es el identificador idempotente de eventos. No se usa `event_uuid` como unico porque Cowrie puede repetirlo en varios eventos.
- El pipeline y las migraciones se ejecutan dentro de Docker; no requieren Python instalado en el host.
- La simulacion de descargas usa payloads inocuos servidos dentro de la red LAB.
