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
pipeline-worker: interno, sin puerto publicado
```

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
n8n/workflows/oscorp-workflow.json
pipeline/contracts/
docs/evidencias/
ESTADO_Y_ROADMAP.md
```

## Notas

- `.env` queda fuera de git.
- `n8n` está fijado por defecto en la versión `2.15.0`.
- `event_hash` es el identificador idempotente de eventos. No se usa `event_uuid` como único porque Cowrie puede repetirlo en varios eventos.
- El pipeline y las migraciones se ejecutan dentro de Docker; no requieren Python instalado en el host.
- La simulación de descargas usa payloads inocuos servidos dentro de la red LAB.
