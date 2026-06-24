# oscorp-honeypot-lab

Laboratorio OSCORP refactorizado para ejecutar un honeypot SSH con dos modos:

- `lab`: entorno local reproducible con Cowrie, attacker-sim, n8n, PostgreSQL, Elasticsearch y Kibana.
- `real`: entorno preparado para procesar logs de una VPS externa sin levantar Cowrie local.

## Requisitos

- Docker Desktop
- PowerShell
- Python 3 disponible en el host para ejecutar el procesador local

## Levantar modo LAB

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

El pipeline lee:

```text
cowrie/logs/cowrie.json
```

Y escribe en:

```text
PostgreSQL: tabla eventos
Elasticsearch: indice cowrie-events
```

## Artefactos importantes

```text
docker-compose.yml
.env.example
postgres/init.sql
attacker-sim/
scripts/process_cowrie_ndjson.py
scripts/run_pipeline.ps1
n8n/workflows/oscorp-workflow.json
docs/evidencias/
ESTADO_Y_ROADMAP.md
```

## Notas

- `.env` queda fuera de git.
- `n8n` está fijado por defecto en la versión `2.15.0`.
- `event_hash` es el identificador idempotente de eventos. No se usa `event_uuid` como único porque Cowrie puede repetirlo en varios eventos.
