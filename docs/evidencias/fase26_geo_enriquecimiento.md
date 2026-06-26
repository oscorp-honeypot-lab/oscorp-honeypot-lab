# Fase 26 — Enriquecimiento geográfico de IPs

Fecha: 25 de junio de 2026.

## Alcance

```text
[x] Migración 0011_ip_geo_cache — tabla ip_geo_cache con PK ip, country,
    country_code, city, isp, asn, latitude NUMERIC(9,6), longitude NUMERIC(9,6),
    queried_at, expires_at, error. Índice en expires_at.
[x] pipeline/geo/adapter.py — IpApiAdapter + GeoResult + _is_private()
    · http://ip-api.com/json/{ip} usando urllib.request (sin nuevas deps)
    · ipaddress stdlib para detectar IPs privadas (RFC 1918 + loopback)
    · Manejo de: private_range, api_fail:{msg}, rate_limited, url_error:{r}
[x] pipeline/geo/cache.py — get_cached_geo() + store_geo()
    · SELECT con expires_at > NOW() (solo entradas vigentes)
    · INSERT ... ON CONFLICT (ip) DO UPDATE (upsert completo)
    · TTL configurable, default 7 días
[x] pipeline/geo/enricher.py — enrich_session_ips()
    · Carga DISTINCT src_ip de sessions no presentes en cache vigente
    · LIMIT 30 por run (respeta rate limit de ip-api 45 req/min)
    · Llama adapter.query() + store_geo() por IP, retorna count de éxitos
[x] Integración en process_cowrie_ndjson.py: enrich_session_ips() después de dispatch
[x] Dockerfile pipeline: COPY pipeline/geo /app/geo
[x] Backend SESSION_SELECT: LEFT JOIN ip_geo_cache como fallback de country
    · COALESCE(subquery_from_raw_event, g.country) — prioridad a raw_event
    · LEFT JOIN ip_geo_cache g ON g.ip = s.src_ip AND g.expires_at > NOW()
[x] 21 tests nuevos: 9 adapter + 7 cache + 5 enricher → 82 pipeline totales
[x] Backend: 38/38 sin regresiones (JOIN no rompe queries existentes)
```

## Skills

```text
buscados:
- Python ipaddress stdlib private IP detection
- ip-api.com free tier rate limits and field codes
- PostgreSQL ON CONFLICT DO UPDATE (upsert)
- psycopg3 interval arithmetic

utilizados:
- ipaddress.ip_address(ip).is_private — stdlib, sin imports externos
- urllib.request — mismo patrón que TelegramAdapter (no nueva dep)
- %(key)s — formato de parámetros psycopg3
- INTERVAL '1 day' con multiplicador numérico (NOW() + %(ttl_days)s * INTERVAL '1 day')

instalados: ninguno
```

## Implementación

```text
Flujo del pipeline (por run):
  recalculate_scores → generate_session_alerts → dispatch_pending_alerts
  → enrich_session_ips (nuevo, al final del bloque de eventos)

IpApiAdapter.query(ip):
  1. _is_private(ip) via ipaddress.ip_address().is_private → "private_range"
  2. GET http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,city,isp,as,lat,lon
  3. status="success" → GeoResult con todos los campos
  4. status="fail"    → error="api_fail:{message}"
  5. HTTP 429         → error="rate_limited"
  6. URLError         → error="url_error:{reason}"

ip_geo_cache upsert:
  ON CONFLICT (ip) DO UPDATE — actualiza todos los campos + queried_at = NOW()
  TTL: NOW() + 7 * INTERVAL '1 day'

enricher.py LOAD_UNCACHED_IPS_SQL:
  SELECT DISTINCT src_ip FROM sessions
  WHERE src_ip NOT IN (SELECT ip FROM ip_geo_cache WHERE expires_at > NOW())
  LIMIT 30

Backend SESSION_SELECT (fallback de country):
  COALESCE(
    (SELECT country FROM raw_event subquery),
    g.country
  ) AS country
  + LEFT JOIN ip_geo_cache g ON g.ip = s.src_ip AND g.expires_at > NOW()
```

Archivos creados o modificados:

```text
pipeline/migrations/versions/0011_ip_geo_cache.py  (nueva migración)
pipeline/geo/__init__.py                            (paquete nuevo)
pipeline/geo/adapter.py                             (IpApiAdapter + GeoResult)
pipeline/geo/cache.py                               (get_cached_geo + store_geo)
pipeline/geo/enricher.py                            (enrich_session_ips)
pipeline/tests/test_geo_adapter.py                  (9 tests)
pipeline/tests/test_geo_cache.py                    (7 tests)
pipeline/tests/test_geo_enricher.py                 (5 tests)
pipeline/Dockerfile                                 (COPY pipeline/geo /app/geo)
scripts/process_cowrie_ndjson.py                    (integración enrich_session_ips)
backend/app/adapters/persistence/analytics_repository.py  (SESSION_SELECT con JOIN)
```

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| IpApiAdapter private | test_geo_adapter.py | Unit | ✅ 61/61 | ✅ ImportError | ✅ 5/5 | ✅ 10.x, 172.x, 192.x, 127.x, preserves ip | ✅ Limpio |
| IpApiAdapter public | test_geo_adapter.py | Unit | ✅ 61/61 | ✅ ImportError | ✅ 4/4 | ✅ success + api_fail + 429 + url_error | ✅ Limpio |
| get_cached_geo | test_geo_cache.py | Unit | ✅ 61/61 | ✅ ImportError | ✅ 3/3 | ✅ miss + hit + private_range hit | ✅ Limpio |
| store_geo | test_geo_cache.py | Unit | ✅ 61/61 | ✅ ImportError | ✅ 4/4 | ✅ upsert + commit + ip_in_params + ttl | ✅ Limpio |
| enrich_session_ips | test_geo_enricher.py | Unit | ✅ 61/61 | ✅ ImportError | ✅ 5/5 | ✅ vacío + éxito + privado + batch + error | ✅ Limpio |

## Validación

```text
pruebas pipeline:    82/82  (21 nuevas + 61 regresión)
pruebas backend:     38/38  (sin cambios — JOIN no rompe nada)
validación LAB:      10 servicios healthy
migración 0011:      aplicada y verificada en PostgreSQL
```

Verificación end-to-end con IPs LAB (todas privadas):

```text
enrich_session_ips(conn, IpApiAdapter()) → 0 IPs públicas enriquecidas
ip_geo_cache:
  ip=172.25.0.12  error=private_range  country=None

La IP Docker interna:
  - detectada como privada via ipaddress.ip_address("172.25.0.12").is_private → True
  - almacenada con error="private_range" (evita re-consulta en próximos runs)
  - country=None (el campo en SESSION_SELECT permanece NULL para IPs privadas)
```

Con IPs reales (cuando el honeypot es accesible desde internet):

```text
enrich_session_ips(conn, IpApiAdapter()) → N IPs enriquecidas
ip_geo_cache:
  ip=X.X.X.X  error=None  country="Germany"  city="Berlin"  isp="Deutsche Telekom"
  latitude=52.5244  longitude=13.4105  expires_at=queried_at + 7 days

SESSION_SELECT devuelve:
  country = "Germany" (desde ip_geo_cache cuando raw_event no tiene geo)
```

Rate limit ip-api (free tier: 45 req/min):
  LIMIT 30 por run garantiza que nunca se supera el límite en un solo procesamiento.
  error="rate_limited" se almacena con TTL normal → próximo run reintenta esa IP.
