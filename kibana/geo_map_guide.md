# Guía: mapa geográfico en Kibana

## Prerequisito: mapping geo_point

El campo `src_location` (tipo `geo_point`) ya está definido en el índice
`cowrie-events`. Se aplica automáticamente desde Fase 29 cada vez que el
pipeline procesa eventos con IP pública geolocalizada.

Verificar:

```
GET http://elasticsearch:9200/cowrie-events/_mapping
→ "src_location": { "type": "geo_point" }
```

## Crear el mapa en Kibana

### 1. Crear el index pattern (Data View)

1. Kibana → Stack Management → Index Patterns (o Data Views)
2. Crear nuevo: `cowrie-events`
3. Campo de tiempo: `timestamp_evento`

### 2. Crear una visualización Maps

1. Kibana → Maps → Create map
2. Add layer → Documents
3. Index pattern: `cowrie-events`
4. Geo field: `src_location`
5. Configurar:
   - Layer style: Heat map o Cluster
   - Tooltip fields: `src_ip`, `eventid`, `sensor`, `username`
6. Guardar como "OSCORP — Origen de ataques SSH"

### 3. Añadir al dashboard operativo

1. Kibana → Dashboard → Dashboard operativo (Fase 32)
2. Add panel → Saved visualizations → "OSCORP — Origen de ataques SSH"

## Nota sobre el LAB

El LAB usa IPs privadas (172.25.0.x) que el enriquecedor geo detecta como
`private_range`. Estas IPs **no tienen coordenadas** → `src_location` no se
indexa en esos documentos → el mapa aparece vacío en el LAB.

Con un honeypot expuesto a internet (IPs públicas), el mapa mostrará el origen
real de los ataques.

## Campos disponibles para filtros

| Campo          | Tipo       | Uso                           |
|----------------|------------|-------------------------------|
| `src_location` | geo_point  | Posición geográfica del atacante |
| `src_ip`       | ip         | Filtrar por IP específica     |
| `eventid`      | keyword    | Tipo de evento Cowrie         |
| `username`     | keyword    | Usuario SSH intentado         |
| `sensor`       | keyword    | Sensor/honeypot origen        |
| `timestamp_evento` | date   | Filtro temporal               |
