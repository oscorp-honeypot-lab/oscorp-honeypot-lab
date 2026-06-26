# Fase 28 — Enriquecimiento aplicado al Risk Score

Fecha: 25 de junio de 2026.

## Alcance

```text
[x] Ruleset v1.1.0: habilitadas las dos reglas antes reservadas.
    · malicious_hash_reputation (weight=20): activa cuando VT reporta hashes
      maliciosos en la sesión (error IS NULL AND malicious > 0 en vt_hash_cache).
    · cloud_origin (weight=10): activa cuando el ISP o ASN del src_ip pertenece
      a un proveedor cloud/hosting conocido (ip_geo_cache, expires_at > NOW()).
[x] scoring.py: is_cloud_provider(isp, asn) — función pura pública con
    _CLOUD_KEYWORDS frozenset (amazon, aws, google, microsoft, azure,
    digitalocean, linode, vultr, ovh, hetzner, cloudflare, fastly, akamai,
    tencent, alibaba, huawei).
[x] SessionRiskInput: 2 nuevos campos con defaults seguros:
    · vt_malicious_hashes: int = 0
    · is_cloud_origin: bool = False
    Los defaults garantizan que tests anteriores no se rompan.
[x] LOAD_SESSIONS_SQL: LEFT JOIN vt_hash_cache (subquery count malicious) y
    LEFT JOIN ip_geo_cache (isp, asn para cloud detection).
    Comportamiento cuando enriquecimiento falta o está vencido:
    · expires_at > NOW() filtra datos vencidos → campo queda NULL → default=0/False
    · Sin datos de VT → vt_malicious_hashes=0 → regla NO dispara (conservador)
    · IP privada o sin geo → is_cloud_origin=False → regla NO dispara
[x] Recalculación masiva: recalculate_risk_scores.py recalculó 75 sesiones LAB
    con reglas 1.1.0 almacenadas en session_risk_scores.
[x] Backend: rules_version "1.0.0" → "1.1.0" en main.py (×2),
    analytics_repository.py (×1) y fixture de test de integración.
[x] test_risk_rules.py actualizado: +3 tests nuevos, 2 tests actualizados
    (reflejan estado real de v1.1.0).
[x] test_risk_scoring.py actualizado: +14 tests nuevos en EnrichmentScoringTests
    y CloudDetectionTests.
[x] 17 tests nuevos pipeline (neto) → 119 pipeline totales; 44 backend sin cambios.
```

## Skills

```text
buscados:
- Frozenset para keyword lookup eficiente en Python
- PostgreSQL subquery con JOIN en GROUP BY
- Semver bump y compatibilidad de datos en BD (PK compuesta session_key + rules_version)

utilizados:
- frozenset + any(kw in text for kw in keywords): O(k) lookup eficiente
- psycopg3 GROUP BY con columnas de LEFT JOIN: g.isp y g.asn en SELECT y GROUP BY
- COALESCE con subquery anidada para default 0 cuando no hay datos VT

instalados: ninguno
```

## Implementación

```text
Scoring logic:
  malicious_hash_reputation → session.vt_malicious_hashes > 0
    evidence: ("vt:malicious:{N}",)  donde N = count de hashes maliciosos
  cloud_origin → session.is_cloud_origin is True
    evidence: ("enrichment.network_origin",)

Cloud detection keywords (case-insensitive substring match en ISP + ASN):
  amazon, aws, google, microsoft, azure, digitalocean, linode, vultr,
  ovh, hetzner, cloudflare, fastly, akamai, tencent, alibaba, huawei

Comportamiento cuando enriquecimiento falta o está vencido:
  · VT sin datos: vt_malicious_hashes=0 → NO dispara malicious_hash_reputation
  · VT con error (rate_limited, etc.): vt.error IS NOT NULL → no cuenta → NO dispara
  · IP privada: no hay entrada en ip_geo_cache → isp=NULL, asn=NULL → is_cloud_provider=False
  · Caché expirada: expires_at > NOW() filtra → mismo caso que sin datos

Compatibilidad de BD:
  · session_risk_scores tiene PK (session_key, rules_version)
  · Scores v1.0.0 permanecen en BD (historial)
  · recalculate_scores upsert con v1.1.0 → nuevas filas para todas las sesiones
  · Backend consulta rules_version='1.1.0' → ve scores actualizados

LOAD_SESSIONS_SQL nueva estructura:
  SELECT ... , COALESCE(subquery_vt_malicious, 0) AS vt_malicious_count,
               g.isp, g.asn
  FROM sessions s
  LEFT JOIN eventos e ON ...
  LEFT JOIN ip_geo_cache g ON g.ip = s.src_ip AND g.expires_at > NOW()
  WHERE ...
  GROUP BY s.session_key, s.has_successful_login, s.has_download, g.isp, g.asn
```

Archivos creados o modificados:

```text
pipeline/risk/rules.py                              (v1.1.0, 2 reglas habilitadas)
pipeline/risk/scoring.py                            (is_cloud_provider + 2 nuevos campos + handlers)
pipeline/risk/storage.py                            (LOAD_SESSIONS_SQL + load_session_inputs ext.)
pipeline/tests/test_risk_rules.py                   (+3 nuevos, 2 actualizados)
pipeline/tests/test_risk_scoring.py                 (+14 nuevos: 7 EnrichmentScoring + 7 CloudDetection)
backend/app/main.py                                 (rules_version 1.0.0→1.1.0 ×2)
backend/app/adapters/persistence/analytics_repository.py  (rules_version 1.0.0→1.1.0)
backend/tests/integration/test_analytics_api.py    (fixture rules_version 1.0.0→1.1.0)
```

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| Ruleset v1.1.0 / reglas habilitadas | test_risk_rules.py | Unit | ✅ 102/102 | ✅ AssertionError | ✅ 9/9 | ✅ version + 2 rules + no reserved | ✅ Limpio |
| EnrichmentScoringTests | test_risk_scoring.py | Unit | ✅ 102/102 | ✅ ImportError | ✅ 7/7 | ✅ VT=0 + VT>0 + cloud=F + cloud=T + ambos + cap + evidence | ✅ Limpio |
| CloudDetectionTests | test_risk_scoring.py | Unit | ✅ 102/102 | ✅ ImportError | ✅ 7/7 | ✅ amazon + aws_asn + google + digitalocean + residential + none + empty | ✅ Limpio |
| Backend version bump | test_analytics_api.py | Integration | ✅ 44/44 | actualizado fixture | ✅ 44/44 | fixture usa 1.1.0 → filtro risk_level=high funciona | ✅ Limpio |

## Validación

```text
pruebas pipeline:  119/119  (17 nuevas + 102 regresión)
pruebas backend:    44/44   (sin cambios de tests, versión actualizada)
validación LAB:    10 servicios healthy
recalculación:     75 sesiones actualizadas a v1.1.0
```

Verificación con LAB (IPs privadas Docker, sin descargas):

```text
recalculate_scores → rules_version=1.1.0, sessions_scored=75

Todas las sesiones LAB:
  · vt_malicious_hashes=0 (no hay eventos cowrie.session.file.download)
  · is_cloud_origin=False (IPs 172.25.0.x → private_range en ip_geo_cache → isp=NULL)
  → malicious_hash_reputation NO dispara
  → cloud_origin NO dispara

Scores v1.1.0 en BD son idénticos a v1.0.0 para datos del LAB:
  esto es CORRECTO — el enriquecimiento solo afecta cuando hay datos reales.
```

Con datos reales (honeypot en internet):

```text
Sesión con hash malicioso detectado por VT:
  vt_malicious_hashes=1 → malicious_hash_reputation dispara (+20 puntos)
  evidence: ["vt:malicious:1"]

Sesión desde AWS (IP pública enriquecida con isp="Amazon.com"):
  is_cloud_origin=True → cloud_origin dispara (+10 puntos)
  evidence: ["enrichment.network_origin"]

Sesión con ambos: score += 30, potencialmente sube de HIGH a CRITICAL.
```
