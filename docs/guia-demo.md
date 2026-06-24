# Guia demo - OSCORP Honeypot Lab

## 1. Levantar el laboratorio

```powershell
docker compose --profile lab up -d
```

Validar contenedores:

```powershell
docker compose ps
```

## 2. Generar actividad de ataque

```powershell
docker compose --profile lab run --rm attacker-sim ./run_scenario.sh full
```

## 3. Confirmar eventos en Cowrie

```powershell
(Get-Content cowrie\logs\cowrie.json).Count
```

Eventos esperados:

```text
cowrie.login.failed
cowrie.login.success
cowrie.command.input
cowrie.session.file_download
```

## 4. Procesar el log

```powershell
.\scripts\run_pipeline.ps1
```

Resultado esperado:

```text
events_read=<cantidad>
postgres_ingest=ok
elasticsearch_indexed=<cantidad>
```

## 5. Verificar PostgreSQL

```powershell
docker compose exec postgres psql -U oscorp -d oscorp -c "SELECT COUNT(*) FROM eventos;"
docker compose exec postgres psql -U oscorp -d oscorp -c "SELECT eventid, COUNT(*) FROM eventos GROUP BY eventid ORDER BY COUNT(*) DESC;"
```

## 6. Verificar Elasticsearch

```powershell
Invoke-RestMethod -Uri http://localhost:9200/cowrie-events/_count
```

## 7. Abrir herramientas

```text
n8n:    http://localhost:5678
Kibana: http://localhost:5601
```
