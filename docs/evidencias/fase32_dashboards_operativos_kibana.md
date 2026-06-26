# Fase 32 - Dashboards operativos de Kibana

Fecha: 26 de junio de 2026.

## Alcance

```text
[x] Crear el data view de cowrie-events.
[x] Crear paneles de eventos, sesiones y evolucion temporal.
[x] Crear filtros y tablas operativas.
[x] Validar los paneles con datos LAB.
```

## Implementacion

```text
scripts/configure_kibana_phase32.ps1
  - valida que Kibana este disponible.
  - valida que cowrie-events exista y tenga documentos.
  - crea o reutiliza el data view cowrie-events con timestamp_evento.
  - crea visualizaciones legacy idempotentes:
      OSCORP - Eventos totales
      OSCORP - Evolucion temporal de eventos
      OSCORP - Eventos por tipo
      OSCORP - Sesiones activas por eventos
      OSCORP - IPs origen principales
  - crea la tabla operativa:
      OSCORP - Eventos operativos
  - arma el dashboard:
      OSCORP - Dashboard operativo

scripts/validate_kibana_phase32.ps1
  - valida data view, dashboard, visualizaciones y tabla guardada.
  - ejecuta agregaciones de Elasticsearch equivalentes a los paneles.
```

## Uso

```powershell
docker compose --profile lab up -d
.\scripts\configure_kibana_phase32.ps1
.\scripts\validate_kibana_phase32.ps1
```

Si PowerShell bloquea scripts por politica local:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\configure_kibana_phase32.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate_kibana_phase32.ps1
```

Dashboard:

```text
http://localhost:5601/app/dashboards#/view/oscorp-phase32-operational
```

## Paneles

```text
Eventos:
  - Total de eventos en la ventana temporal.
  - Distribucion por eventid.

Sesiones:
  - Tabla de session_id y src_ip ordenada por cantidad de eventos.

Evolucion temporal:
  - Histograma sobre timestamp_evento.

Operacion:
  - Tabla Discover con timestamp_evento, eventid, src_ip, username,
    session_id, command_input, url, shasum y sensor.
  - Tabla de IPs origen principales para filtrar desde el dashboard.
```

## Validacion LAB

Validacion ejecutada contra LAB local levantado:

```text
Kibana: available
Elasticsearch: cowrie-events con 2451 documentos
Data view: 618e5a78-418f-40db-bf11-cc269ad6dd34 / timestamp_evento
Dashboard: oscorp-phase32-operational
Objetos guardados: 1 dashboard, 5 visualizaciones, 1 busqueda guardada
Consultas base: sesiones, eventid, src_ip y date_histogram con buckets
Visual: 6 paneles renderizados, sin errores de carga, datos visibles en tablas
```

## Limites

```text
La fase 32 crea objetos dentro de la instancia Kibana local.
La exportacion versionada a kibana/dashboards.ndjson queda para Fase 33.

El mapa geografico se mantiene documentado en kibana/geo_map_guide.md.
En LAB las IPs privadas no generan coordenadas reales; con modo REAL el campo
src_location permite activar Maps sobre ataques de origen publico.
```
