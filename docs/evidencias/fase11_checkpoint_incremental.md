# Fase 11 - Checkpoint e idempotencia del workflow

Fecha: 25 de junio de 2026.

## Objetivo

Procesar únicamente las líneas nuevas de `cowrie.json`, conservar el avance
después de reinicios y recuperar el flujo sin pérdida ante reemplazo o
truncado del archivo.

## Skills

Se buscaron Skills para lectura incremental de NDJSON, cursor persistente,
rotación de logs y n8n.

Se utilizaron:

```text
- n8n-workflow
- python-expert-best-practices-code-review
```

No se instaló una Skill adicional: los resultados descubiertos no aportaban
un patrón más específico que las capacidades ya disponibles.

## Persistencia

La migración `0002_pipeline_checkpoints` crea:

```text
pipeline_checkpoints
- source_key
- file_device
- file_inode
- fingerprint_hash
- fingerprint_bytes
- byte_offset
- line_number
- file_size
- last_run_id
- reset_count
- last_reset_reason
- updated_at
```

También amplía `pipeline_runs` con:

```text
- source_key
- mode
- source_offset_start
- source_offset_end
- checkpoint_reset_reason
```

## Algoritmo

1. El modo `incremental` consulta el checkpoint en PostgreSQL.
2. El lector abre Cowrie en binario y comienza en `byte_offset`.
3. Solo confirma líneas terminadas con salto de línea.
4. Una línea parcial queda pendiente para la siguiente ejecución.
5. PostgreSQL y Elasticsearch se procesan antes de avanzar el checkpoint.
6. El checkpoint y el cierre de `pipeline_runs` se confirman juntos.
7. Un fallo previo al commit vuelve a procesar el lote; `event_hash` evita
   duplicados.

El fingerprint se calcula sobre bytes ya confirmados del mismo descriptor de
archivo leído.

## Rotación y truncado

```text
Tamaño actual menor al offset:
  reset a byte 0 con razón file_truncated

Fingerprint inicial diferente:
  reset a byte 0 con razón file_replaced

Mismo contenido y reinicio del contenedor:
  conserva offset y continúa sin reprocesar
```

Los resets pueden releer eventos conocidos, pero no perderlos. PostgreSQL usa
`event_hash` único y Elasticsearch usa el mismo hash como `_id`.

El modo `recovery` siempre relee el archivo completo y no modifica el
checkpoint incremental.

## Pruebas automáticas

La imagen `oscorp/pipeline:phase11` incluye cinco pruebas:

```text
test_append_reads_only_new_complete_lines ... ok
test_partial_line_remains_pending ........... ok
test_replacement_with_different_prefix ...... ok
test_restart_keeps_existing_offset .......... ok
test_truncation_resets_to_start ............. ok
```

## Validación operativa

Bootstrap del checkpoint:

```text
run_id=59
events_read=422
source_offset_start=0
source_offset_end=237156
```

Ejecución sucesiva:

```text
run_id=60
events_read=0
source_offset_start=237156
source_offset_end=237156
```

Después de reiniciar `pipeline-worker`:

```text
run_id=61
events_read=0
source_offset_start=237156
source_offset_end=237156
```

Smoke test con ataque nuevo:

```text
run_id=64
events_read=106
events_inserted=106
events_indexed=106
source_offset_start=237156
source_offset_end=296660

run_id=65
events_read=0
events_inserted=0
events_indexed=0
source_offset_start=296660
source_offset_end=296660
```

Recuperación manual:

```text
run_id=66
mode=recovery
events_read=528
events_inserted=0
events_indexed=528
checkpoint_before=296660
checkpoint_after=296660
```

Estado acumulado:

```text
PostgreSQL:
- 1602 eventos
- 1602 hashes únicos
- 275 sesiones
- 37 pipeline_runs

Elasticsearch:
- 1602 documentos

Checkpoint:
- source_key: cowrie_ndjson
- byte_offset: 296660
- line_number: 528
- last_run_id incremental: 69
- reset_count: 0
```

## Reproducibilidad

El commit candidato se validó desde un clon sin `.env`, logs ni volúmenes
previos.

```text
- setup.ps1 superado
- Alembic 0002 aplicado sobre PostgreSQL vacío
- cinco pruebas unitarias superadas
- checkpoint inicial en byte 0
- reinicio del worker con events_read=0
- validate_n8n_contract.ps1 superado
- ataque e ingesta incremental: 106 eventos
- segunda ejecución: events_read=0
- PostgreSQL: 106 eventos y 106 hashes únicos
- Elasticsearch: 106 documentos
- sesiones: 15
- pipeline_runs: 7
- checkpoint final: byte 59504, línea 106
- reset_count: 0
- smoke_test.ps1 -NoBuild superado
```
