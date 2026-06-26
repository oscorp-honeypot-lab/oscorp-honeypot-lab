# Fase 29 — Visualización geográfica

Fecha: 25 de junio de 2026.

## Alcance

```text
[x] Elasticsearch: campo src_location (tipo geo_point) añadido al mapping de
    cowrie-events. ensure_index() crea el campo en índices nuevos;
    _update_index_geo_mapping() lo añade a índices ya existentes (idempotente).
[x] Pipeline: build_geo_lookup(connection, src_ips) carga lat/lon desde
    ip_geo_cache para las IPs del lote; index_events() acepta geo_lookup y
    añade src_location a cada documento donde haya coordenadas.
[x] Backend: GET /api/v1/analytics/geo-stats — top 20 países por sesiones,
    totales (with_geo, without_geo, unique_countries).
[x] Frontend: GeoPanel en DashboardPage — stats row + tabla de países con flags
    + estado vacío descriptivo para IPs privadas del LAB.
[x] Kibana: kibana/geo_map_guide.md — guía para crear el mapa Maps en Kibana
    (prerequisito del índice ya satisfecho; mapa real en Fase 32).
[x] 9 tests nuevos pipeline + 6 tests nuevos backend → 128 pipeline, 50 backend.
```

## Skills

```text
buscados:
- geo_point en Elasticsearch: tipo nativo para coordenadas, indexable espacialmente
- PUT /index/_mapping: añade nuevos campos a índice existente (idempotente, sin reindexar)
- Unicode Regional Indicators: código U+1F1E6 + offset de letra A = bandera de país

utilizados:
- put /_mapping con {properties: {src_location: {type: "geo_point"}}}: añade campo sin reindexar
- geo_location_for_ip(lat, lon) → {lat, lon} | None: función pura, fácil de testear
- build_geo_lookup(connection, src_ips): batch lookup lat/lon por IP del lote
- String.fromCodePoint(char.charCodeAt(0) + 127397): bandera emoji sin dependencias

instalados: ninguno
```

## Implementación

```text
Elasticsearch geo_point:
  ensure_index() ya incluye src_location en el mapping inicial.
  Para índices existentes: _update_index_geo_mapping() hace PUT /{index}/_mapping
  con solo el campo nuevo. Los documentos existentes no se reindexan automáticamente;
  solo los nuevos lotes tendrán src_location.

Pipeline flow:
  1. enrich_session_ips(connection, IpApiAdapter())   → llena ip_geo_cache
  2. enrich_download_hashes(connection, VirusTotalAdapter())
  3. src_ips = {e["src_ip"] for e in events if e.get("src_ip")}
  4. geo_lookup = build_geo_lookup(connection, src_ips)  → {ip: {lat, lon}}
  5. index_events(..., geo_lookup=geo_lookup)            → añade src_location

Backend SQL:
  Totales: COUNT DISTINCT session_key con LEFT JOIN ip_geo_cache,
  filtros: g.ip IS NOT NULL AND g.error IS NULL AND g.country IS NOT NULL.
  Por país: JOIN (no LEFT) para solo sesiones con geo + GROUP BY country, country_code
  ORDER BY session_count DESC LIMIT 20.

Frontend GeoPanel:
  - Refetch cada 5 minutos (datos geo cambian poco)
  - countryFlag(code): convierte código ISO-2 en emoji de bandera (zero-deps)
  - Estado vacío descriptivo: explica que LAB usa IPs privadas → sin geo

LAB validation:
  - ip_geo_cache: todas las IPs son private_range → total_with_geo=0, by_country=[]
  - GeoPanel muestra estado vacío con mensaje informativo (correcto)
  - ES mapping verificado: src_location: {type: "geo_point"} en cowrie-events
```

Archivos creados o modificados:

```text
pipeline/geo/elasticsearch.py                       (nuevo: geo_location_for_ip + build_geo_lookup)
pipeline/tests/test_geo_elasticsearch.py            (nuevo: 9 tests)
scripts/process_cowrie_ndjson.py                    (ensure_index + geo_point + index_events geo_lookup)
backend/app/domain/analytics.py                     (GeoCountryStat + GeoStats)
backend/app/domain/ports/analytics_repository.py    (get_geo_stats Protocol)
backend/app/application/analytics_service.py        (get_geo_stats delegate)
backend/app/adapters/persistence/analytics_repository.py  (get_geo_stats SQL)
backend/app/api/schemas.py                          (GeoCountryStatResponse + GeoStatsResponse)
backend/app/api/v1/analytics.py                     (GET /analytics/geo-stats)
backend/tests/unit/test_geo_service.py              (nuevo: 3 tests)
backend/tests/integration/test_geo_api.py           (nuevo: 3 tests)
frontend/src/api/generated/                         (SDK regenerado con geo-stats)
frontend/src/api/client.ts                          (getGeoStats)
frontend/src/features/dashboard/DashboardPage.tsx   (query + GeoPanel + countryFlag)
frontend/src/styles/global.css                      (estilos GeoPanel)
kibana/geo_map_guide.md                             (guía creación mapa Kibana)
```

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| geo_location_for_ip | test_geo_elasticsearch.py | Unit | ✅ 119/119 | ✅ ImportError | ✅ 5/5 | ✅ lat=None, lon=None, ambos=None, int coercion | ✅ Limpio |
| build_geo_lookup | test_geo_elasticsearch.py | Unit | ✅ 119/119 | ✅ ImportError | ✅ 4/4 | ✅ empty, match, null lat/lon, múltiples | ✅ Limpio |
| GeoStats service | test_geo_service.py | Unit | ✅ 119/119 | ✅ ImportError | ✅ 3/3 | ✅ empty, breakdown, totals | ✅ Limpio |
| geo-stats endpoint | test_geo_api.py | Integration | ✅ 44/44 | ✅ ImportError | ✅ 3/3 | ✅ 401 + 200 + fields | ✅ Limpio |

## Validación

```text
pruebas pipeline:  128/128  (9 nuevas + 119 regresión)
pruebas backend:    50/50   (6 nuevas + 44 regresión)
TypeScript:         0 errores
```

Verificación LAB:

```text
GET /api/v1/analytics/geo-stats:
  total_with_geo: 0
  total_without_geo: 75
  unique_countries: 0
  by_country: []

Esto es CORRECTO: IPs del LAB (172.25.x.x) son private_range → no hay
coordenadas en ip_geo_cache → sin geo_point en documentos ES → sin países.

Con IPs públicas reales:
  - ip_geo_cache tiene lat/lon reales → geo_lookup no vacío
  - Documentos ES incluyen src_location: {lat: X, lon: Y}
  - /geo-stats devuelve top países con session_count y unique_ips
  - GeoPanel muestra tabla de banderas con datos reales
  - Kibana Maps puede crear heat map / cluster sobre src_location

Elasticsearch mapping:
  PUT cowrie-events/_mapping → acknowledged: true
  GET cowrie-events/_mapping → src_location: {type: "geo_point"}
```
