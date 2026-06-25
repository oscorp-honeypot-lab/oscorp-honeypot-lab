# Fase 12 - Trazabilidad y recuperación

Fecha: 25 de junio de 2026.

## Implementación

Migración `0003_pipeline_traceability`:

```text
pipeline_runs:
- request_id único
- triggered_by
- attempt_count
- error_code
- error_detail

pipeline_event_errors:
- run_id
- source_key
- line_number
- byte_offset
- error_code
- error_detail
- raw_line
```

Comportamiento:

```text
- una solicitud completada se devuelve sin crear otro run;
- una solicitud fallida reutiliza el mismo run_id;
- attempt_count aumenta por reintento;
- Elasticsearch tiene tres intentos con espera incremental;
- líneas inválidas se aíslan y el checkpoint continúa;
- completed_with_errors distingue errores parciales;
- failed conserva código y detalle técnico.
```

## Validaciones

```text
Pruebas Python: 7 superadas
Reintento idempotente: un request_id, un pipeline_run, attempt_count=2
Cuarentena:
  status=completed_with_errors
  errors_count=1
  error_code=invalid_json
  siguiente ejecución events_read=0
Fallo Elasticsearch:
  primer intento failed
  recuperación con mismo run_id
  attempt_count=2
  events_indexed=2
  status final=completed
Smoke test:
  106 eventos nuevos
  segunda ejecución events_read=0
```

## Estado operativo

```text
PostgreSQL:
- 1710 eventos
- 1710 hashes únicos
- 292 sesiones
- 46 pipeline_runs
- 1 evento en cuarentena

Elasticsearch:
- 1710 documentos

Checkpoint:
- byte_offset=356525
- line_number=637
- last_run_id=78
```

## Clon limpio

```text
- setup y migración 0003 superados
- 7 pruebas Python superadas
- request_id idempotente validado
- cuarentena completed_with_errors validada
- caída y recuperación de Elasticsearch validada
- smoke test superado
- PostgreSQL: 107 eventos y 107 hashes únicos
- Elasticsearch: 107 documentos
- sesiones: 16
- pipeline_runs: 7
- eventos en cuarentena: 1
- checkpoint: byte 59605, línea 108
```
