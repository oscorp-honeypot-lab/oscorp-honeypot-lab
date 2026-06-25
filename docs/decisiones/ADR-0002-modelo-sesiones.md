# ADR-0002 - Modelo de sesiones correlacionadas

Estado: aceptado para implementación.

Fecha: 25 de junio de 2026.

## Contexto

Los eventos Cowrie se almacenan individualmente en `eventos`. La aplicación
necesita una unidad analítica estable para listar sesiones, mostrar actividad,
calcular riesgo y asociar alertas.

El conjunto actual contiene:

```text
292 sesiones
290 completas
2 incompletas
0 sesiones con múltiples IP de origen
```

## Decisión

Se implementará una tabla materializada `sessions`, actualizada mediante
upsert desde el pipeline.

No se utilizará una vista calculada en cada consulta porque las siguientes
fases agregarán score, revisión del analista, enriquecimiento y alertas.

## Identidad

La identidad de dominio será:

```text
session_key = sensor normalizado + ":" + session_id
```

`session_id` no se considera globalmente único entre sensores.

Restricciones:

```text
PRIMARY KEY (session_key)
UNIQUE (sensor, session_id)
session_id NOT NULL
```

Cuando `sensor` no esté disponible se utilizará el valor estable `unknown`.

## Campos propuestos

```text
sessions
- session_key text primary key
- session_id text not null
- sensor text not null
- src_ip inet
- src_port integer
- first_event_at timestamptz not null
- last_event_at timestamptz not null
- connected_at timestamptz
- closed_at timestamptz
- duration_seconds numeric
- lifecycle_status text not null
- event_count integer not null
- login_success_count integer not null
- login_failed_count integer not null
- command_count integer not null
- command_failed_count integer not null
- download_count integer not null
- first_username text
- last_username text
- has_successful_login boolean not null
- has_download boolean not null
- created_at timestamptz not null
- updated_at timestamptz not null
```

Las credenciales, comandos, URLs y hashes completos permanecen en `eventos`.
La sesión conserva solo campos resumidos para evitar duplicación innecesaria.

## Estados

```text
complete
  existe cowrie.session.connect y cowrie.session.closed

open
  existe cowrie.session.connect pero no cowrie.session.closed

incomplete
  no existe cowrie.session.connect o faltan datos mínimos de inicio
```

Una sesión `open` puede pasar a `complete`. Una sesión `incomplete` puede
reconstruirse si llegan eventos anteriores o posteriores.

## Reglas temporales

```text
first_event_at = MIN(timestamp_evento)
last_event_at = MAX(timestamp_evento)
connected_at = MIN(timestamp_evento) de cowrie.session.connect
closed_at = MAX(timestamp_evento) de cowrie.session.closed
duration_seconds =
  closed_at - connected_at cuando ambos existen;
  NULL en sesiones open o incomplete
```

No se usará el campo textual `duration` de Cowrie como fuente principal.

## Contadores

Los contadores se derivan por `eventid`:

```text
login_success_count: cowrie.login.success
login_failed_count: cowrie.login.failed
command_count: cowrie.command.input
command_failed_count: cowrie.command.failed
download_count: cowrie.session.file_download
```

`event_count` incluye todos los eventos asociados a la sesión.

## Índices previstos

```text
idx_sessions_last_event_at
idx_sessions_src_ip
idx_sessions_lifecycle_status
idx_sessions_sensor_session_id unique
idx_sessions_has_successful_login
idx_sessions_has_download
```

## Invariantes

```text
first_event_at <= last_event_at
connected_at <= closed_at cuando ambos existen
duration_seconds >= 0
todos los contadores >= 0
complete exige connected_at y closed_at
open exige connected_at y closed_at NULL
session_key es inmutable
```

## Límites de esta subfase

Fase 13.1 define el modelo. No crea la tabla ni modifica el pipeline.

Las siguientes subfases implementarán:

```text
13.2 agrupación y proyección por session_id
13.3 cálculo temporal y resumen de actividad
13.4 migración, backfill y validación de sesiones completas/incompletas
```
