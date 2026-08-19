-- ============================================================
-- OSCORP ThreatLab — Evidencia numerica, tercera tanda (ultima)
-- Objetivo: caracterizar el MTTD, cuyo promedio global (10,6 dias)
-- no es interpretable como tiempo de deteccion.
--
-- El dispatcher calcula:  mttd_seconds = NOW() - event_timestamp
-- es decir, latencia entre la marca del evento en el sensor y el
-- momento en que el pipeline lo proceso. En modo REAL esa latencia
-- esta dominada por la periodicidad de la sincronizacion, no por
-- la capacidad de deteccion. Estas consultas lo demuestran.
--
--   Get-Content .\docs\evidencias\consultas\evidencia_tesis_03.sql | docker compose exec -T postgres psql -U oscorp -d oscorp | Tee-Object -FilePath .\docs\evidencias\consultas\evidencia_tesis_03_salida.txt
-- ============================================================
-- Ejecutado el 13/08/2026 contra la instancia local (perfil LAB).

\echo '=== K. MTTD desagregado por modo de origen de la sesion — LA CONSULTA CLAVE ==='
SELECT s.source_mode,
       COUNT(*)                                                                     AS alertas,
       ROUND(AVG(a.mttd_seconds), 1)                                                AS promedio_seg,
       MIN(a.mttd_seconds)                                                          AS minimo_seg,
       MAX(a.mttd_seconds)                                                          AS maximo_seg,
       ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY a.mttd_seconds)::numeric, 1) AS p95_seg
FROM alerts a
JOIN sessions s ON s.session_key = a.session_key
WHERE a.mttd_seconds IS NOT NULL
GROUP BY s.source_mode
ORDER BY s.source_mode;

\echo '=== L. MTTD por modo Y disparador ==='
SELECT s.source_mode,
       a.trigger,
       COUNT(*)                      AS alertas,
       ROUND(AVG(a.mttd_seconds), 1) AS promedio_seg,
       MIN(a.mttd_seconds)           AS minimo_seg,
       MAX(a.mttd_seconds)           AS maximo_seg
FROM alerts a
JOIN sessions s ON s.session_key = a.session_key
WHERE a.mttd_seconds IS NOT NULL
GROUP BY s.source_mode, a.trigger
ORDER BY s.source_mode, alertas DESC;

\echo '=== M. Distribucion de MTTD en tramos ==='
SELECT CASE
         WHEN mttd_seconds <     60 THEN 'a. menos de 1 minuto'
         WHEN mttd_seconds <   3600 THEN 'b. 1 minuto a 1 hora'
         WHEN mttd_seconds <  86400 THEN 'c. 1 hora a 1 dia'
         WHEN mttd_seconds < 604800 THEN 'd. 1 a 7 dias'
         ELSE                            'e. mas de 7 dias'
       END                    AS tramo,
       COUNT(*)               AS alertas,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS porcentaje
FROM alerts
WHERE mttd_seconds IS NOT NULL
GROUP BY tramo
ORDER BY tramo;

\echo '=== N. MTTD promedio por jornada de disparo ==='
SELECT triggered_at::date          AS jornada,
       COUNT(*)                    AS alertas,
       ROUND(AVG(mttd_seconds), 1) AS promedio_seg,
       MAX(mttd_seconds)           AS maximo_seg
FROM alerts
WHERE mttd_seconds IS NOT NULL
GROUP BY triggered_at::date
ORDER BY jornada;

\echo '=== O. Los 5 MTTD mas altos, con sus marcas temporales ==='
SELECT s.source_mode,
       a.trigger,
       a.event_timestamp,
       a.triggered_at,
       ROUND(a.mttd_seconds / 86400.0, 2) AS mttd_dias
FROM alerts a
JOIN sessions s ON s.session_key = a.session_key
WHERE a.mttd_seconds IS NOT NULL
ORDER BY a.mttd_seconds DESC
LIMIT 5;

\echo '=== P. Las 4 alertas pendientes: que son ==='
SELECT trigger, channel, status, attempt_count, triggered_at, error_code
FROM alerts
WHERE status = 'pending'
ORDER BY triggered_at;

\echo '=== Q. Mediana y percentil 90 del MTTD por origen ==='
SELECT s.source_mode,
       COUNT(*) AS alertas,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY a.mttd_seconds)::numeric, 1) AS mediana_seg,
       ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY a.mttd_seconds)::numeric, 1) AS p90_seg
FROM alerts a
JOIN sessions s ON s.session_key = a.session_key
WHERE a.mttd_seconds IS NOT NULL
GROUP BY s.source_mode;

\echo '=== FIN — anotar fecha y commit ==='
