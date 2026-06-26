# Fase 27 — Enriquecimiento de hashes con VirusTotal

Fecha: 25 de junio de 2026.

## Alcance

```text
[x] Migración 0012_vt_hash_cache — tabla vt_hash_cache con sha256 PK,
    malicious, suspicious, undetected, harmless, timeout (todos INTEGER),
    last_analysis_date BIGINT (Unix ts), reputation INTEGER,
    queried_at TIMESTAMP TZ server_default NOW(), expires_at TZ, error TEXT.
[x] pipeline/vt/adapter.py — VirusTotalAdapter + VtResult
    · GET https://www.virustotal.com/api/v3/files/{sha256}
    · Header: x-apikey (VT_API_KEY env var, sin nueva dependencia — urllib.request)
    · Sin clave: error="no_api_key" (silent skip sin tocar DB)
    · HTTP 429 → "rate_limited"
    · HTTP 404 → "not_found"
    · HTTP 5xx → "http_error:{code}"
    · URLError → "url_error:{reason}"
[x] pipeline/vt/cache.py — get_cached_vt() + store_vt()
    · SELECT con expires_at > NOW() (solo entradas vigentes)
    · INSERT ... ON CONFLICT (sha256) DO UPDATE (upsert completo)
    · TTL configurable, default 30 días (VT análisis estable)
[x] pipeline/vt/enricher.py — enrich_download_hashes()
    · SELECT DISTINCT shasum FROM eventos WHERE eventid='cowrie.session.file.download'
      AND shasum NOT IN (SELECT sha256 FROM vt_hash_cache WHERE expires_at > NOW())
      LIMIT 10  ← respeta rate limit gratuito de VT (4 req/min)
    · No almacena resultados con error="no_api_key" (permite enriquecer al añadir clave)
    · Retorna count de éxitos (error IS NULL)
[x] Integración en process_cowrie_ndjson.py: enrich_download_hashes() después de enrich_session_ips
[x] Dockerfile pipeline: COPY pipeline/vt /app/vt
[x] Backend: dominio VtStats + port + service + repositorio PostgreSQL + schema + endpoint
    GET /api/v1/analytics/vt-stats → {total_cached, malicious_detected, not_found, error_count, max_malicious}
[x] 20 tests nuevos pipeline: 8 adapter + 7 cache + 5 enricher → 102 pipeline totales
[x] 6 tests nuevos backend: 3 unit + 3 integration → 44 backend totales
```

## Skills

```text
buscados:
- VirusTotal API v3 file lookup (no upload)
- VT free tier rate limits (4 req/min, 500/day)
- Manejo de API key segura via env var (no hardcoding)

utilizados:
- urllib.request.Request con headers → mismo patrón que TelegramAdapter
- os.environ.get("VT_API_KEY") → None seguro cuando clave no configurada
- %(key)s psycopg3, BIGINT para last_analysis_date (Unix timestamp puede ser largo)

instalados: ninguno
```

## Implementación

```text
Flujo del pipeline (por run):
  recalculate_scores → generate_session_alerts → dispatch_pending_alerts
  → enrich_session_ips → enrich_download_hashes (nuevo, al final)

VirusTotalAdapter.query(sha256):
  1. Sin clave → VtResult(error="no_api_key"), SIN llamada HTTP
  2. GET https://www.virustotal.com/api/v3/files/{sha256} x-apikey:{key}
  3. JSON ok → VtResult con last_analysis_stats, last_analysis_date, reputation
  4. HTTP 429 → "rate_limited"
  5. HTTP 404 → "not_found"
  6. HTTP 5xx → "http_error:{code}"
  7. URLError → "url_error:{reason}"

vt_hash_cache upsert:
  ON CONFLICT (sha256) DO UPDATE → actualiza todos los campos + queried_at = NOW()
  TTL: NOW() + 30 * INTERVAL '1 day'

enricher lógica no_api_key:
  if result.error != "no_api_key":  → no se almacena (reintento al configurar clave)
      store_vt(connection, result, ttl_days=ttl_days)
  if result.error is None:
      enriched += 1

VtStats SQL:
  SELECT
    COUNT(*)                                            total_cached,
    COUNT(*) FILTER (WHERE error IS NULL AND malicious > 0)  malicious_detected,
    COUNT(*) FILTER (WHERE error = 'not_found')        not_found,
    COUNT(*) FILTER (WHERE error IS NOT NULL)          error_count,
    MAX(malicious)                                     max_malicious
  FROM vt_hash_cache WHERE expires_at > NOW()
```

Archivos creados o modificados:

```text
pipeline/migrations/versions/0012_vt_hash_cache.py         (nueva migración)
pipeline/vt/__init__.py                                     (paquete nuevo)
pipeline/vt/adapter.py                                      (VirusTotalAdapter + VtResult)
pipeline/vt/cache.py                                        (get_cached_vt + store_vt)
pipeline/vt/enricher.py                                     (enrich_download_hashes)
pipeline/tests/test_vt_adapter.py                           (8 tests)
pipeline/tests/test_vt_cache.py                             (7 tests)
pipeline/tests/test_vt_enricher.py                          (5 tests)
pipeline/Dockerfile                                         (COPY pipeline/vt /app/vt)
scripts/process_cowrie_ndjson.py                            (integración enrich_download_hashes)
backend/app/domain/analytics.py                             (VtStats dataclass)
backend/app/domain/ports/analytics_repository.py            (get_vt_stats protocol)
backend/app/application/analytics_service.py                (get_vt_stats delegate)
backend/app/adapters/persistence/analytics_repository.py    (get_vt_stats SQL)
backend/app/api/schemas.py                                  (VtStatsResponse)
backend/app/api/v1/analytics.py                             (GET /analytics/vt-stats)
backend/tests/unit/test_vt_service.py                       (3 unit tests)
backend/tests/integration/test_vt_api.py                    (3 integration tests)
```

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| VirusTotalAdapter no_key | test_vt_adapter.py | Unit | ✅ 82/82 | ✅ ImportError | ✅ 3/3 | ✅ error + sha256 + fields=None | ✅ Limpio |
| VirusTotalAdapter public | test_vt_adapter.py | Unit | ✅ 82/82 | ✅ ImportError | ✅ 5/5 | ✅ success+429+404+url_error+503 | ✅ Limpio |
| get_cached_vt | test_vt_cache.py | Unit | ✅ 82/82 | ✅ ImportError | ✅ 3/3 | ✅ miss + hit + malicious_count | ✅ Limpio |
| store_vt | test_vt_cache.py | Unit | ✅ 82/82 | ✅ ImportError | ✅ 4/4 | ✅ upsert + commit + sha256 + ttl | ✅ Limpio |
| enrich_download_hashes | test_vt_enricher.py | Unit | ✅ 82/82 | ✅ ImportError | ✅ 5/5 | ✅ empty+success+error+no_key+batch | ✅ Limpio |
| VtStats service | test_vt_service.py | Unit | ✅ 38/38 | ✅ ImportError | ✅ 3/3 | ✅ empty + values + error_count | ✅ Limpio |
| vt-stats endpoint | test_vt_api.py | Integration | ✅ 38/38 | ✅ 401 | ✅ 200 + structure | ✅ numeric fields | ✅ Limpio |

## Validación

```text
pruebas pipeline:  102/102  (20 nuevas + 82 regresión)
pruebas backend:    44/44   (6 nuevas + 38 regresión)
validación LAB:    10 servicios healthy
migración 0012:    aplicada y verificada en PostgreSQL
```

Verificación end-to-end con LAB (sin descargas reales):

```text
enrich_download_hashes(conn, VirusTotalAdapter()) → 0 (no hay eventos cowrie.session.file.download)
vt_hash_cache rows: 0

GET /api/v1/analytics/vt-stats → 200 OK
{"total_cached": 0, "malicious_detected": 0, "not_found": 0, "error_count": 0, "max_malicious": null}
```

Con descargas reales (cowrie.session.file.download con shasum):

```text
enrich_download_hashes(conn, VirusTotalAdapter()) → N hashes enriquecidos
vt_hash_cache:
  sha256=abc...  malicious=25  suspicious=1  reputation=-22  error=NULL
  expires_at=queried_at + 30 days

GET /api/v1/analytics/vt-stats →
{"total_cached": N, "malicious_detected": M, "not_found": K, "error_count": 0, "max_malicious": 25}
```

Rate limit VT (free: 4 req/min, 500/day):
  LIMIT 10 por run garantiza <10 req/run, muy por debajo del límite gratuito.
  error="rate_limited" no se almacena (reintento automático en próximo run).
  error="no_api_key" no se almacena (reintento automático al configurar VT_API_KEY).
