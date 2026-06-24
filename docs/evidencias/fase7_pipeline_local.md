# Fase 7 - Pipeline local Cowrie a PostgreSQL y Elasticsearch

## Objetivo

Procesar el archivo NDJSON generado por Cowrie en modo LAB y persistir sus eventos en:

```text
PostgreSQL -> tabla eventos
Elasticsearch -> indice cowrie-events
```

## Correccion aplicada antes de procesar

Se corrigio el modelo de eventos porque `event_uuid` no puede ser unico. En Cowrie, el campo `uuid` puede repetirse en varios eventos de la misma sesion.

Se agrego `event_hash` como identificador idempotente calculado con SHA-256 sobre cada linea NDJSON.

## Comando ejecutado

```powershell
.\scripts\run_pipeline.ps1
```

Equivalente directo:

```powershell
python scripts\process_cowrie_ndjson.py --log cowrie\logs\cowrie.json --project-dir .
```

## Resultado observado

```text
events_read=366
postgres_ingest=ok
elasticsearch_indexed=366
```

Se reejecuto el pipeline para confirmar idempotencia. PostgreSQL se mantuvo en 366 eventos unicos y Elasticsearch se mantuvo en 366 documentos.

## Verificacion PostgreSQL

```text
eventos: 366
hashes unicos: 366
sesiones: 48
```

Auditoria final en `pipeline_runs`:

```text
events_read=366
events_indexed=366
status=completed
```

Eventos principales:

```text
64 cowrie.command.input
48 cowrie.session.connect
48 cowrie.session.closed
42 cowrie.client.version
42 cowrie.client.kex
36 cowrie.login.success
32 cowrie.session.params
32 cowrie.log.closed
8  cowrie.session.file_download
4  cowrie.login.failed
2  cowrie.command.failed
```

## Verificacion Elasticsearch

```text
indice: cowrie-events
documentos: 366
```

## Artefactos agregados

```text
scripts/process_cowrie_ndjson.py
scripts/run_pipeline.ps1
n8n/workflows/oscorp-workflow.json
```

## Nota sobre n8n

Se dejo un workflow importable como referencia en `n8n/workflows/oscorp-workflow.json`.

El procesador versionado en `scripts/process_cowrie_ndjson.py` queda como camino reproducible de validacion automatica para evitar depender de clicks manuales o credenciales locales de la UI de n8n.
