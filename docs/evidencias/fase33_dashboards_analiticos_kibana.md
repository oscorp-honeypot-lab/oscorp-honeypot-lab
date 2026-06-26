# Fase 33 - Dashboards analiticos de Kibana versionados

Fecha: 26 de junio de 2026.

## Alcance

```text
[x] Crear visualizaciones de riesgo y mapa geografico.
[x] Exportar objetos a kibana/dashboards.ndjson.
[x] Automatizar o documentar la importacion.
[x] Validar exportacion e importacion desde una instancia limpia.
```

## Implementacion

```text
scripts/configure_kibana_phase33.ps1
  - asegura cowrie-events.src_location como geo_point.
  - crea/sincroniza oscorp-session-risk desde PostgreSQL.
  - crea data views para cowrie-events y oscorp-session-risk.
  - crea visualizaciones de riesgo:
      OSCORP - Distribucion de riesgo
      OSCORP - Histograma de score
      OSCORP - Sesiones high critical
  - crea tabla:
      OSCORP - Sesiones de mayor riesgo
  - crea mapa:
      OSCORP - Mapa geografico de ataques
  - crea dashboard:
      OSCORP - Dashboard analitico
  - exporta la capa versionada a kibana/dashboards.ndjson.

scripts/import_kibana_dashboards.ps1
  - importa kibana/dashboards.ndjson en el space indicado.

scripts/validate_kibana_phase33.ps1
  - valida indices, objetos, dashboard, export y clean import.
  - crea un space limpio temporal, importa el NDJSON y valida dashboards.
```

## Uso

```powershell
docker compose --profile lab up -d
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\configure_kibana_phase32.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\configure_kibana_phase33.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate_kibana_phase33.ps1
```

Importacion manual desde el artefacto versionado:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\import_kibana_dashboards.ps1
```

Dashboard:

```text
http://localhost:5601/app/dashboards#/view/oscorp-phase33-analytics
```

Ventana temporal por defecto: `now-30d` para que el LAB incluya los eventos
de junio 2026 y el dashboard muestre datos sin ajuste manual.

## Datos analiticos

```text
Indice Elasticsearch: oscorp-session-risk
Origen: PostgreSQL sessions + session_risk_scores
Documentos LAB: 398 sesiones
Rango de score LAB: 0 a 60
Promedio LAB: 15.57
Distribucion LAB:
  low: 207
  medium: 190
  high: 1
  critical: 0
```

## Mapa geografico

```text
El dashboard incluye un panel Maps sobre cowrie-events.src_location.
En LAB las IPs son privadas y no generan coordenadas, por lo que el mapa puede
renderizar sin puntos. En modo REAL, los documentos con IP publica y
src_location poblaran el mapa sin cambiar el dashboard importado.
```

## Validacion esperada

```text
Kibana: available
oscorp-session-risk: documentos sincronizados
cowrie-events: mapping src_location geo_point
Objetos guardados: dashboard, mapa, 3 visualizaciones y 1 busqueda guardada
Export: kibana/dashboards.ndjson
Clean import: importacion correcta en un space temporal limpio
```

Nota: Kibana 8 puede reasignar IDs al importar objetos compartibles entre
spaces; el validador acepta `originId` y titulo para comprobar la importacion
sin acoplarse al ID fisico generado en el space temporal.

## Validacion ejecutada

```text
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\configure_kibana_phase33.ps1
resultado: OK

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate_kibana_phase32.ps1
resultado: OK, 2451 documentos en cowrie-events

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate_kibana_phase33.ps1
resultado: OK
  risk docs: 398
  high/critical docs: 1
  geo docs con src_location: 0
  clean import: OK en space temporal

npm run build
resultado: OK
nota: Vite informa warning de chunk > 500 kB, no bloqueante.
```

Validacion visual en navegador integrado:

```text
URL:
http://localhost:5601/app/dashboards#/view/oscorp-phase33-analytics?_g=(filters:!(),refreshInterval:(pause:!t,value:60000),time:(from:now-30d,to:now))

Resultado:
  - 5 paneles renderizados.
  - distribucion de riesgo visible.
  - histograma de score visible.
  - tabla high/critical con 1 documento: riesgo high, score 60.
  - mapa renderizado con layer "Origen de ataques SSH".
  - sin senales de error visibles.
  - 0 errores nuevos de consola durante la ultima carga.
```
