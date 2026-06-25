# Fase 13 - Sesiones correlacionadas

Fecha: 25 de junio de 2026.

## Implementación

```text
- migración 0004_correlated_sessions
- tabla materializada sessions
- backfill desde eventos
- upsert incremental por sensor y session_id
- estados complete, open e incomplete
- timestamps, duración y contadores de actividad
```

La validación creó una sesión `open`, agregó su cierre y confirmó la
transición a `complete` con duración de 5 segundos.

## Resultado

```text
sessions: 308
event_count acumulado: 1818
complete: 306
open: 0
incomplete: 2
con login exitoso: 168
con descargas: 17
invariantes inválidas: 0
Alembic: 0004_correlated_sessions
smoke test: superado
pipeline_runs: 51
último run_id: 83
checkpoint: byte 416383
PostgreSQL / Elasticsearch: 1818 / 1818
```

La suma de `sessions.event_count` coincide con todos los eventos asociados a
una sesión.

## Validación desde clon limpio

```text
instalación desde cero: superada
transición open -> complete: superada
eventos PostgreSQL / Elasticsearch: 108 / 108
sesiones correlacionadas: 16
eventos duplicados en segunda ingesta: 0
```

La primera ejecución del clon reveló que `Add-Content -Encoding UTF8` podía
agregar BOM al primer evento de un archivo vacío. El validador ahora escribe
NDJSON mediante `UTF8Encoding(false)` y falla de forma explícita si la sesión
sintética no fue persistida.
