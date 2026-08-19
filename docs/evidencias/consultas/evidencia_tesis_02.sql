-- ============================================================
-- OSCORP ThreatLab — Evidencia numerica, segunda tanda
-- Cierra: distribucion de riesgo por version de reglas,
--         jornadas efectivas del sensor REAL,
--         MTTD actualizado y causa raiz de los fallos de entrega.
--
--   docker cp .\evidencia_tesis_2.sql oscorp_postgres:/tmp/e2.sql
--   docker compose exec -T postgres psql -U oscorp -d oscorp -f /tmp/e2.sql > evidencia_tesis_2_salida.txt
-- ============================================================
-- Ejecutado el 19/08/2026 contra la instancia local (perfil LAB).

\echo '=== A. Distribucion de riesgo POR VERSION DE REGLAS ==='
SELECT rules_version, risk_level, COUNT(*) AS sesiones
FROM session_risk_scores
GROUP BY rules_version, risk_level
ORDER BY rules_version, risk_level;

\echo '=== B. Sesiones sin puntaje bajo la version activa 1.1.0 (debe dar 0) ==='
SELECT COUNT(*) AS sesiones_sin_score_110
FROM sessions s
LEFT JOIN session_risk_scores r
       ON r.session_key = s.session_key
      AND r.rules_version = '1.1.0'
WHERE r.session_key IS NULL;

\echo '=== C. Jornadas efectivas de operacion del sensor REAL — cierra N10 ==='
SELECT timestamp_evento::date        AS jornada,
       COUNT(*)                      AS eventos,
       COUNT(DISTINCT session_id)    AS sesiones,
       COUNT(DISTINCT src_ip)        AS ips_unicas
FROM eventos
WHERE source_mode = 'real'
GROUP BY timestamp_evento::date
ORDER BY jornada;

\echo '=== D. MTTD global actualizado (reemplaza las cifras de la Captura 4) ==='
SELECT COUNT(*)                                                              AS alertas_totales,
       COUNT(mttd_seconds)                                                   AS alertas_con_mttd,
       ROUND(AVG(mttd_seconds), 1)                                           AS promedio_seg,
       MIN(mttd_seconds)                                                     AS minimo_seg,
       MAX(mttd_seconds)                                                     AS maximo_seg,
       ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY mttd_seconds)::numeric, 1) AS p95_seg
FROM alerts;

\echo '=== E. MTTD por disparador ==='
SELECT trigger,
       COUNT(*)                    AS alertas,
       ROUND(AVG(mttd_seconds), 1) AS promedio_seg,
       MIN(mttd_seconds)           AS minimo_seg,
       MAX(mttd_seconds)           AS maximo_seg
FROM alerts
GROUP BY trigger
ORDER BY alertas DESC;

\echo '=== F. Estados de entrega y tasa de fallo actual ==='
SELECT status,
       COUNT(*)                                              AS alertas,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)    AS porcentaje
FROM alerts
GROUP BY status
ORDER BY alertas DESC;

\echo '=== G. Causa raiz de los fallos: ventana temporal de cada codigo de error ==='
SELECT error_code,
       COUNT(*)            AS ocurrencias,
       MIN(triggered_at)   AS primer_fallo,
       MAX(triggered_at)   AS ultimo_fallo,
       COUNT(DISTINCT triggered_at::date) AS jornadas_afectadas
FROM alerts
WHERE error_code IS NOT NULL
GROUP BY error_code
ORDER BY ocurrencias DESC;

\echo '=== H. Muestra del detalle de error (para identificar la causa exacta) ==='
SELECT error_code, LEFT(error_detail, 160) AS detalle, COUNT(*) AS ocurrencias
FROM alerts
WHERE error_code IS NOT NULL
GROUP BY error_code, LEFT(error_detail, 160)
ORDER BY ocurrencias DESC
LIMIT 10;

\echo '=== I. Fallos por jornada (para ver si se concentran en un periodo) ==='
SELECT triggered_at::date AS jornada,
       COUNT(*) FILTER (WHERE status = 'sent')  AS enviadas,
       COUNT(*) FILTER (WHERE status <> 'sent') AS fallidas
FROM alerts
GROUP BY triggered_at::date
ORDER BY jornada;

\echo '=== J. Coherencia PostgreSQL vs. total esperado en Elasticsearch ==='
SELECT COUNT(*) AS eventos_en_postgres FROM eventos;

\echo '=== FIN — anotar fecha y commit ==='
