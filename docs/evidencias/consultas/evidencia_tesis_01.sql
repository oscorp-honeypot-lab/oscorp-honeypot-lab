-- ============================================================
-- OSCORP ThreatLab — Evidencia numérica para la tesis (v3)
-- Ejecutar con el stack levantado, desde la raíz del repositorio:
--
--   Get-Content evidencia_tesis.sql | docker compose exec -T postgres psql -U oscorp -d oscorp
--
-- Guardar la salida completa: agregar  > evidencia_tesis_salida.txt
-- Anotar la FECHA y el COMMIT en el que se ejecutó.
-- ============================================================

\echo '=== 1. Unicidad de event_hash — indicador del 3.4.1 ==='
SELECT COUNT(*)                              AS total_eventos,
       COUNT(DISTINCT event_hash)            AS hashes_distintos,
       COUNT(*) - COUNT(DISTINCT event_hash) AS duplicados
FROM eventos;

\echo '=== 2. Integridad de campos obligatorios — indicador de falsacion del 3.4.3 ==='
SELECT COUNT(*) AS eventos_incompletos
FROM eventos
WHERE event_hash IS NULL OR source_mode IS NULL;

\echo '=== 3. Desglose de EVENTOS por origen ==='
SELECT source_mode, COUNT(*) AS eventos
FROM eventos
GROUP BY source_mode
ORDER BY source_mode;

\echo '=== 4. Desglose de SESIONES por origen (5.2.1) ==='
SELECT source_mode, COUNT(*) AS sesiones
FROM sessions
GROUP BY source_mode
ORDER BY source_mode;

\echo '=== 5. Ventana temporal del sensor REAL — cierra N10 ==='
SELECT MIN(timestamp_evento)                                       AS inicio_real,
       MAX(timestamp_evento)                                       AS cierre_real,
       (MAX(timestamp_evento)::date - MIN(timestamp_evento)::date) AS dias_calendario,
       COUNT(DISTINCT timestamp_evento::date)                      AS dias_con_actividad,
       COUNT(*)                                                    AS eventos_real
FROM eventos
WHERE source_mode = 'real';

\echo '=== 5b. Ventana temporal del modo LAB (para contraste) ==='
SELECT MIN(timestamp_evento) AS inicio_lab,
       MAX(timestamp_evento) AS cierre_lab
FROM eventos
WHERE source_mode = 'lab';

\echo '=== 6. Distribucion de niveles de riesgo (5.1.2) ==='
SELECT r.risk_level, COUNT(*) AS sesiones
FROM session_risk_scores r
GROUP BY r.risk_level
ORDER BY COUNT(*) DESC;

\echo '=== 7. Top-5 de sesiones por puntaje — respalda la explicacion de N13 ==='
SELECT s.session_key,
       s.source_mode,
       r.score,
       r.risk_level,
       s.has_successful_login,
       s.has_download,
       s.command_count,
       r.reasons
FROM session_risk_scores r
JOIN sessions s ON s.session_key = r.session_key
ORDER BY r.score DESC, s.last_event_at DESC
LIMIT 5;

\echo '=== 8. Version activa de reglas aplicada a los puntajes ==='
SELECT rules_version, COUNT(*) AS sesiones_puntuadas
FROM session_risk_scores
GROUP BY rules_version;

\echo '=== 9. Sesiones sin puntaje (deberia dar 0) ==='
SELECT COUNT(*) AS sesiones_sin_score
FROM sessions s
LEFT JOIN session_risk_scores r ON r.session_key = s.session_key
WHERE r.session_key IS NULL;

\echo '=== 10. Alertas por disparador y tasa de fallo (5.4) ==='
SELECT trigger,
       COUNT(*)                                       AS total,
       COUNT(*) FILTER (WHERE status = 'sent')        AS enviadas,
       COUNT(*) FILTER (WHERE status <> 'sent')       AS fallidas
FROM alerts
GROUP BY trigger
ORDER BY total DESC;

\echo '=== 11. Codigos de error de entrega — pendiente declarado en 5.4 ==='
SELECT error_code, COUNT(*) AS ocurrencias
FROM alerts
WHERE error_code IS NOT NULL
GROUP BY error_code
ORDER BY ocurrencias DESC;

\echo '=== FIN — anotar fecha y commit de esta ejecucion ==='
