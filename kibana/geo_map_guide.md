# Guia: mapa geografico en Kibana

## Prerequisito: mapping geo_point

El campo `src_location` debe existir como `geo_point` en el indice
`cowrie-events`. Desde Fase 33, el script de configuracion lo asegura de forma
idempotente:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\configure_kibana_phase33.ps1
```

Verificar manualmente:

```text
GET http://localhost:9200/cowrie-events/_mapping
-> "src_location": { "type": "geo_point" }
```

## Crear el mapa automaticamente

Fase 33 crea el objeto:

```text
OSCORP - Mapa geografico de ataques
```

Tambien lo agrega al dashboard:

```text
http://localhost:5601/app/dashboards#/view/oscorp-phase33-analytics
```

## Crear el mapa manualmente

### 1. Crear el data view

1. Kibana -> Stack Management -> Data Views.
2. Crear nuevo: `cowrie-events`.
3. Campo de tiempo: `timestamp_evento`.

### 2. Crear una visualizacion Maps

1. Kibana -> Maps -> Create map.
2. Add layer -> Documents.
3. Data view: `cowrie-events`.
4. Geo field: `src_location`.
5. Configurar:
   - Layer style: Heat map o Cluster.
   - Tooltip fields: `src_ip`, `eventid`, `sensor`, `username`.
6. Guardar como `OSCORP - Mapa geografico de ataques`.

### 3. Anadir al dashboard analitico

1. Kibana -> Dashboard -> `OSCORP - Dashboard analitico`.
2. Add panel -> Maps -> `OSCORP - Mapa geografico de ataques`.

## Nota sobre el LAB

El LAB usa IPs privadas de Docker. Estas IPs no tienen coordenadas publicas,
por lo que `src_location` puede existir en el mapping pero no en los documentos.
En ese caso el mapa renderiza sin puntos.

Con un honeypot expuesto a internet y eventos de IP publica enriquecidos, el
mismo mapa mostrara el origen real de los ataques sin cambiar el dashboard.

## Campos disponibles para filtros

| Campo              | Tipo      | Uso                            |
|--------------------|-----------|--------------------------------|
| `src_location`     | geo_point | Posicion geografica del origen |
| `src_ip`           | ip        | Filtrar por IP especifica      |
| `eventid`          | keyword   | Tipo de evento Cowrie          |
| `username`         | keyword   | Usuario SSH intentado          |
| `sensor`           | keyword   | Sensor/honeypot origen         |
| `timestamp_evento` | date      | Filtro temporal                |
