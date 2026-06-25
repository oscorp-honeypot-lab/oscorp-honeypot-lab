# Fase 24 - Entrega de alertas por Telegram

Fecha: 25 de junio de 2026.

## Alcance

```text
[x] Migración 0010_alert_attempt_count — agrega attempt_count INTEGER NOT NULL DEFAULT 0
[x] CHECK(attempt_count >= 0) en tabla alerts
[x] pipeline/alerts/telegram.py — TelegramAdapter (urllib.request, sin deps nuevas)
[x] TelegramAdapter.from_env() — configura desde TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
[x] Operación silenciosa cuando las variables no están configuradas
[x] format_alert_message() — HTML para Telegram con label, sesión, riesgo, timestamp
[x] pipeline/alerts/dispatcher.py — dispatch_pending_alerts(connection, adapter)
[x] Carga hasta 50 alertas pending por run (channel='telegram')
[x] Marca sent con sent_at=NOW() y mttd_seconds calculado
[x] Reintentos: attempt_count++ por fallo; status='failed' al llegar a MAX_ATTEMPTS=3
[x] error_code y error_detail persistidos en fallos
[x] Integración en process_cowrie_ndjson.py post-generate_session_alerts
[x] TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en docker-compose.yml (vacíos por defecto)
[x] 15 pruebas telegram + 7 pruebas dispatcher = 22 pruebas nuevas → 51 pipeline total
[x] Flujo completo validado con mock adapter: 12 alertas enviadas, mttd_seconds registrado
[x] Reintentos validados: attempt_count=2 + fallo → status=failed, error_code=http_429
```

## Skills

```text
buscados:
- Python urllib.request Telegram Bot API
- psycopg retry pattern with attempt_count
- unittest.mock patch urllib.request.urlopen

utilizados existentes:
- urllib.request (Python stdlib — sin dependencias nuevas)
- psycopg (UPDATE con CASE WHEN)
- unittest.mock (patch para tests de HTTP)

instalados:
- ninguno (urllib.request ya disponible en Python stdlib)
```

## Implementación

```text
adaptador Telegram:
  TelegramAdapter.from_env() → None si TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID vacíos
  send(message) → (True, None) | (False, error_detail)
  URL: https://api.telegram.org/bot{token}/sendMessage
  parse_mode: HTML (para negritas y código en el mensaje)
  timeout: 10 segundos

mensaje formateado:
  <b>OSCORP ThreatLab — Alerta</b>
  {trigger label}
  Sesión: <code>{session_key}</code>
  Riesgo: {emoji} {risk_level} · {risk_score}
  Evento: {event_timestamp}

dispatcher:
  - carga pending WHERE channel='telegram' AND attempt_count < 3 ORDER BY triggered_at LIMIT 50
  - por cada alerta: send → si ok → status=sent, sent_at, mttd_seconds
                              si fallo → attempt_count++, error_code, error_detail
                                         si attempt_count >= MAX_ATTEMPTS → status=failed
  - commit por alerta (no transacción global: fallo en una no revierte las demás)

integración:
  recalculate_scores → generate_session_alerts → dispatch_pending_alerts (nuevo)

configuración sin secretos versionados:
  docker-compose.yml usa ${TELEGRAM_BOT_TOKEN:-} y ${TELEGRAM_CHAT_ID:-}
  el usuario define estas variables en su .env local (no versionado)
```

Archivos creados o modificados:

```text
pipeline/migrations/versions/0010_alert_attempt_count.py  (nuevo)
pipeline/alerts/telegram.py                               (nuevo)
pipeline/alerts/dispatcher.py                             (nuevo)
pipeline/tests/test_telegram.py                           (nuevo — 15 tests)
pipeline/tests/test_alert_dispatcher.py                   (nuevo — 7 tests)
scripts/process_cowrie_ndjson.py                          (integración dispatcher)
docker-compose.yml                                        (TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID)
```

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| TelegramAdapter from_env | test_telegram.py | Unit | ✅ 29/29 | ✅ ImportError | ✅ 4/4 | ✅ token-only, chat-only, ambos, ninguno | ✅ Limpio |
| TelegramAdapter send | test_telegram.py | Unit | ✅ 29/29 | ✅ ImportError | ✅ 3/3 | ✅ success + HTTPError + URLError | ✅ Limpio |
| format_alert_message | test_telegram.py | Unit | ✅ 29/29 | ✅ ImportError | ✅ 8/8 | ✅ 3 triggers + 2 emojis + score + timestamp | ✅ Limpio |
| dispatch_pending_alerts | test_alert_dispatcher.py | Unit | ✅ 29/29 | ✅ ImportError | ✅ 7/7 | ✅ None + vacío + éxito + fallo + max_attempts + batch | ✅ Limpio |

## Validación

```text
pruebas pipeline:    51/51  (22 nuevas + 29 regresión)
pruebas backend:     30/30  (sin cambios)
validación LAB:      superada con 10 servicios persistentes
migración 0010:      aplicada y verificada en PostgreSQL
```

Verificación de la columna attempt_count:

```sql
attempt_count | integer | not null | 0
"ck_alerts_attempt_count" CHECK (attempt_count >= 0)
```

Verificación end-to-end con mock adapter:

```text
dispatch_pending_alerts(conn, MockAdapter()) → 12 alertas enviadas
  status: sent
  sent_at: 2026-06-25 22:10:13
  mttd_seconds: 4209.44 (tiempo real evento → envío)

Verificación reintentos:
  alert con attempt_count=2 + FailAdapter(429) → status=failed, attempt_count=3, error_code=http_429
```

Mensaje Telegram formateado (muestra):

```html
<b>OSCORP ThreatLab — Alerta</b>
Login exitoso en honeypot
Sesión: <code>39de0cde0136:0304355ee525</code>
Riesgo: 🟡 medium · 25
Evento: 2026-06-25 21:00:04.374875+00:00
```

Activación en producción:

```bash
# En el .env local (no versionar):
TELEGRAM_BOT_TOKEN=bot123:ABCD...
TELEGRAM_CHAT_ID=-100123456789

# Luego:
docker compose --profile lab up -d pipeline-worker
```

Validación de los 10 servicios LAB:

```text
oscorp_cowrie            Up (healthy)
oscorp_attacker_sim      Up
oscorp_postgres          Up (healthy)
oscorp_elasticsearch     Up (healthy)
oscorp_kibana            Up (healthy)
oscorp_n8n               Up (healthy)
oscorp_pipeline_worker   Up (healthy)
oscorp_payload_server    Up
oscorp_backend           Up (healthy)
oscorp_frontend          Up (healthy)
```

La Fase 24 queda completa. El siguiente trabajo corresponde a la Fase 25:
medición real de MTTD (promedios, percentil 95, latencia por tipo de evento).
