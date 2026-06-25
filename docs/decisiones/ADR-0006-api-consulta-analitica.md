# ADR-0006 - API de consulta analítica

Estado: aceptado.

Fecha: 25 de junio de 2026.

## Decisión

La primera API analítica se implementa como un módulo de lectura separado en
las capas existentes:

```text
api -> application -> domain port -> PostgreSQL adapter
```

Se exponen cuatro operaciones protegidas por el rol mínimo `viewer`:

```text
GET /api/v1/analytics/summary
GET /api/v1/sessions
GET /api/v1/events
GET /api/v1/sessions/{session_key}
```

## Paginación

Los listados usan paginación por desplazamiento con orden estable:

```text
page: mínimo 1
page_size: 1 a 100
sesiones: last_event_at DESC, session_key
eventos: timestamp_evento DESC, id DESC
```

Este esquema es suficiente para el volumen académico actual. La migración a
cursor se evaluará si el volumen REAL demuestra que el desplazamiento deja de
ser adecuado.

## Privacidad

La API no devuelve:

```text
eventos.password
eventos.raw_event
event_hash
tokens o hashes de identidad
```

El detalle de sesión entrega solamente metadatos operativos, comandos,
descargas, línea temporal y el score activo `1.0.0`.

## Persistencia

No se agrega una migración en esta fase. Las consultas principales ya están
respaldadas por índices sobre fecha de sesión, timestamp de evento,
identificador de sesión y versión/score de riesgo.
