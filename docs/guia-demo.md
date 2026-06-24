# Guia demo - OSCORP Honeypot Lab

## 1. Levantar el laboratorio

```powershell
.\scripts\setup.ps1
```

Validar contenedores:

```powershell
docker compose ps
```

## 2. Generar actividad de ataque

```powershell
.\scripts\run_demo.ps1
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

## Smoke test completo

```powershell
.\scripts\smoke_test.ps1
```

El smoke test levanta el LAB, ejecuta una campaña completa, procesa el log y comprueba idempotencia.
