# oscorp-honeypot-lab

OSCORP ThreatLab es un laboratorio local para estudiar ataques contra un
honeypot SSH y convertir esos eventos en datos visibles para una app de
seguridad.

El flujo principal del proyecto es:

```text
attacker-sim -> Cowrie -> n8n/pipeline-worker -> PostgreSQL/Elasticsearch -> app web
                                                         |
                                                         -> alertas Telegram
```

Sirve para probar de forma reproducible:

- ataques simulados e inocuos contra Cowrie;
- procesamiento incremental de `cowrie/logs/cowrie.json`;
- correlacion de sesiones y Attack Risk Score;
- alertas operativas por Telegram;
- visualizacion en la app web propia;
- dashboards de Kibana como apoyo tecnico opcional.

El modo `lab` levanta todo localmente con Docker. El modo `real`, que se
implementara en la siguiente etapa, queda orientado a procesar logs de una VPS
externa sin depender de Cowrie local.

## Clonar el proyecto

```powershell
git clone https://github.com/oscorp-honeypot-lab/oscorp-honeypot-lab.git
cd oscorp-honeypot-lab
```

Si el repositorio ya estaba clonado:

```powershell
git pull
```

## Requisitos

- Docker Desktop
- PowerShell
- Git

Node.js y Python solo son necesarios si se quiere desarrollar backend o
frontend fuera de Docker. Para usar el LAB normal alcanza con Docker.

## Guia LAB: ataques, Telegram y dashboard

Esta es la ruta recomendada para probar todo lo construido antes de avanzar al
modo REAL: levantar el LAB, generar ataques simulados, procesarlos con
n8n/pipeline, recibir alertas por Telegram y ver los datos en la app web.

### 1. Preparar el LAB por primera vez

Desde la raiz del proyecto:

```powershell
.\scripts\setup.ps1
```

El setup crea `.env` si falta, genera una contrasena administrativa local,
configura la clave estable de n8n, sincroniza el workflow, aplica migraciones y
levanta los contenedores del perfil `lab`.

Despues de esa primera preparacion, para volver a levantar la app con Docker:

```powershell
docker compose --profile lab up -d
```

Servicios principales:

```text
App web:       http://localhost:5173/dashboard
Backend API:   http://localhost:8000/docs
n8n:           http://localhost:5678
Kibana:        http://localhost:5601
Elasticsearch: http://localhost:9200
Cowrie SSH:    localhost:2222
PostgreSQL:    localhost:5433
```

Validacion general del LAB:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate_lab.ps1
```

### Desarrollo: actualizar backend y frontend

Para usar el LAB normal, no hace falta levantar backend ni frontend a mano:
`setup.ps1` y `docker compose --profile lab up -d` dejan todo corriendo.

En este compose, backend y frontend se construyen dentro de imagenes Docker.
Eso significa que, si se cambia codigo del backend o del frontend en el repo,
hay que reconstruir y recrear el servicio correspondiente.

Backend:

```powershell
docker compose build backend
docker compose up -d backend
```

Frontend:

```powershell
docker compose build frontend
docker compose up -d frontend
```

Backend y frontend juntos:

```powershell
docker compose build backend frontend
docker compose up -d backend frontend
```

El frontend ejecuta `npm run dev` dentro del contenedor, pero el codigo queda
copiado en la imagen durante el build. Por eso los cambios hechos en
`frontend/` no se reflejan hasta reconstruir la imagen, salvo que mas adelante
se agregue un compose de desarrollo con volumenes para hot reload.

### 2. Configurar Telegram opcional

Editar el archivo `.env` local y completar:

```text
TELEGRAM_BOT_TOKEN=token_del_bot
TELEGRAM_CHAT_ID=id_del_chat
```

Para obtener esos datos:

- Crear un bot con `@BotFather` en Telegram y copiar el token.
- Enviar un mensaje cualquiera al bot.
- Obtener el `chat_id` con `getUpdates` de Telegram o con el cliente que se use
  para administrar el bot.

No guardar tokens reales en git, capturas, issues ni conversaciones. `.env`
queda fuera del repositorio. El workflow n8n no lleva el secreto embebido: el
envio lo hace `pipeline-worker` leyendo variables de entorno.

Si `.env` se edito con contenedores ya levantados, recrear los servicios que
leen esas variables:

```powershell
docker compose --profile lab up -d --force-recreate pipeline-worker backend
```

Verificar sin imprimir secretos:

```powershell
docker compose exec -T pipeline-worker python -c "import os; print('telegram_configured=' + str(bool(os.getenv('TELEGRAM_BOT_TOKEN') and os.getenv('TELEGRAM_CHAT_ID'))))"
```

Resultado esperado:

```text
telegram_configured=True
```

Si las alertas quedan con `http_400: Bad Request: chat not found`, el token
tiene formato valido pero el bot no puede escribir en ese chat. Revisar:

- abrir una conversacion con el bot y enviar `/start`;
- si es un grupo, agregar el bot al grupo;
- volver a obtener el `chat_id` despues de enviar un mensaje al bot o al grupo;
- actualizar `.env` y recrear los servicios que leen Telegram:

```powershell
docker compose --profile lab up -d --force-recreate pipeline-worker backend
```

### 3. Entrar a la app web

Abrir:

```text
http://localhost:5173/dashboard
```

Usar las credenciales que quedaron en `.env`:

```text
OSCORP_API_ADMIN_USERNAME
OSCORP_API_ADMIN_PASSWORD
```

Si `OSCORP_API_ADMIN_PASSWORD` estaba vacia, `setup.ps1` genera una contrasena
administrativa aleatoria.

### 4. Sincronizar antes del ataque

Este paso deja el checkpoint al dia para que la siguiente ejecucion procese
solo eventos nuevos:

```powershell
.\scripts\run_n8n_pipeline.ps1
```

Si devuelve `events_read=0`, esta bien: significa que no habia eventos
pendientes.

### 5. Generar ataques simulados

Campana completa:

```powershell
docker compose --profile lab run --rm attacker-sim ./run_scenario.sh full
```

Escenarios individuales:

```powershell
# Fuerza bruta controlada contra SSH/Cowrie.
docker compose --profile lab run --rm attacker-sim ./run_scenario.sh brute-force

# Reconocimiento post-login: whoami, id, uname, ps, netstat, etc.
docker compose --profile lab run --rm attacker-sim ./run_scenario.sh recon

# Descarga simulada de payloads inocuos desde payload-server.
docker compose --profile lab run --rm attacker-sim ./run_scenario.sh malware-download
```

Eventos esperados en `cowrie/logs/cowrie.json`:

```text
cowrie.login.failed
cowrie.login.success
cowrie.command.input
cowrie.session.file_download
```

El ataque escribe logs al momento. La app web, PostgreSQL, Elasticsearch y
Telegram se actualizan cuando se ejecuta el pipeline del siguiente paso.

### 6. Procesar eventos y enviar alertas

```powershell
.\scripts\run_n8n_pipeline.ps1
```

Resultado esperado:

```text
events_read       > 0
events_inserted   > 0
events_indexed    > 0
errors_count      = 0
```

Durante esta ejecucion el pipeline:

```text
1. Lee cowrie/logs/cowrie.json desde el ultimo checkpoint.
2. Inserta eventos en PostgreSQL.
3. Indexa documentos en Elasticsearch.
4. Correlaciona sesiones.
5. Recalcula Attack Risk Score.
6. Genera alertas por successful_login, file_download y high_risk.
7. Envia alertas pendientes a Telegram si hay token/chat configurados.
```

### 7. Ver datos en la app, Telegram y bases

En la app:

```text
http://localhost:5173/dashboard
```

Revisar:

```text
- resumen operativo
- evolucion temporal
- distribucion de riesgo
- tabla de sesiones
- detalle de una sesion nueva
- seccion de alertas
```

Ver alertas en PostgreSQL:

```powershell
docker compose exec -T postgres psql -U oscorp -d oscorp -c "SELECT trigger, status, COUNT(*) FROM alerts GROUP BY trigger, status ORDER BY trigger, status;"
```

Si Telegram esta bien configurado, deberian aparecer alertas con `status=sent`.
Si algo falla, revisar `error_code`, `error_detail` y `attempt_count`:

```powershell
docker compose exec -T postgres psql -U oscorp -d oscorp -c "SELECT trigger, status, error_code, attempt_count, sent_at FROM alerts ORDER BY triggered_at DESC LIMIT 10;"
```

Ver conteos de eventos:

```powershell
docker compose exec -T postgres psql -U oscorp -d oscorp -c "SELECT COUNT(*) FROM eventos;"
Invoke-RestMethod -Uri http://localhost:9200/cowrie-events/_count
```

### 8. Demo automatizada opcional

Cuando el LAB ya esta configurado, se puede ejecutar casi todo el flujo en una
sola orden:

```powershell
.\scripts\run_demo.ps1
```

El script valida servicios, sincroniza checkpoint, genera el ataque `full`,
procesa por n8n y comprueba idempotencia.

Para repetir la demo sin correr toda la validacion inicial:

```powershell
.\scripts\run_demo.ps1 -SkipValidation
```

### 9. Kibana opcional

La app web es la vista principal del proyecto. Kibana queda como apoyo tecnico
para inspeccion, analisis y evidencia.

Dashboard operativo:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\configure_kibana_phase32.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate_kibana_phase32.ps1
```

```text
http://localhost:5601/app/dashboards#/view/oscorp-phase32-operational
```

Dashboard analitico:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\configure_kibana_phase33.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate_kibana_phase33.ps1
```

```text
http://localhost:5601/app/dashboards#/view/oscorp-phase33-analytics
```

Importar dashboards desde el artefacto versionado:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\import_kibana_dashboards.ps1
```

## Procesar cowrie.json manualmente

La ejecucion normal del flujo completo se hace desde n8n:

```powershell
.\scripts\run_n8n_pipeline.ps1
```

Este comando queda como mecanismo de recuperacion manual:

```powershell
.\scripts\run_pipeline.ps1
```

El pipeline lee:

```text
cowrie/logs/cowrie.json
```

Y escribe en:

```text
PostgreSQL: tabla eventos
Elasticsearch: indice cowrie-events
```

La ruta normal usa un checkpoint persistente en PostgreSQL y procesa solo
lineas nuevas. `run_pipeline.ps1` mantiene la recuperacion completa sin alterar
ese checkpoint.

## API y dashboard

La API usa sesiones de servidor mediante cookies; no entrega tokens para
guardar en `localStorage`.

Endpoints principales:

```text
POST /api/v1/auth/login
GET  /api/v1/auth/me
POST /api/v1/auth/logout
POST /api/v1/users
GET  /api/v1/analytics/summary
GET  /api/v1/sessions
GET  /api/v1/sessions/{session_key}
PATCH /api/v1/sessions/{session_key}/review
GET  /api/v1/events
GET  /api/v1/exports/sessions.csv
GET  /api/v1/exports/events.csv
```

Las lecturas analiticas requieren una sesion autenticada. Los listados usan
`page` y `page_size` con un maximo de 100 elementos, y no exponen contrasenas
ni el evento crudo almacenado.

Sesiones y eventos aceptan filtros combinables por `from`, `to`, `src_ip`,
`country`, `username` y `event_type`. Las sesiones tambien permiten
`risk_level` y `reviewed`. Marcar una sesion como revisada requiere rol
`analyst` o `admin` y token CSRF.

Las exportaciones CSV reutilizan los mismos filtros, permiten `page` y
`page_size` hasta 1000 filas por archivo, e informan el total disponible en
cabeceras `X-Export-*`. Se generan como UTF-8 con BOM y no incluyen contrasenas
ni eventos crudos.

## Demo y validacion

```powershell
.\scripts\validate_lab.ps1
.\scripts\validate_n8n_contract.ps1
.\scripts\run_demo.ps1
.\scripts\smoke_test.ps1
.\scripts\recalculate_risk_scores.ps1
```

El smoke test comprueba servicios, ataque completo, descarga offline,
orquestacion desde n8n, persistencia, indexacion e idempotencia.

## Administracion

```powershell
.\scripts\backup.ps1
.\scripts\reset_lab.ps1
```

## Artefactos importantes

```text
docker-compose.yml
.env.example
pipeline/migrations/
attacker-sim/
scripts/process_cowrie_ndjson.py
scripts/run_pipeline.ps1
scripts/setup.ps1
scripts/validate_lab.ps1
scripts/validate_n8n_contract.ps1
scripts/validate_checkpoint.ps1
scripts/validate_traceability.ps1
scripts/validate_partial_errors.ps1
scripts/validate_failure_recovery.ps1
scripts/validate_sessions.ps1
scripts/run_demo.ps1
scripts/run_n8n_pipeline.ps1
scripts/smoke_test.ps1
scripts/recalculate_risk_scores.ps1
scripts/validate_risk_scores.ps1
scripts/configure_kibana_phase32.ps1
scripts/configure_kibana_phase33.ps1
scripts/import_kibana_dashboards.ps1
scripts/validate_kibana_phase32.ps1
scripts/validate_kibana_phase33.ps1
kibana/dashboards.ndjson
n8n/workflows/oscorp-workflow.json
pipeline/contracts/
backend/
frontend/
docs/evidencias/
ESTADO_Y_ROADMAP.md
```

## Notas

- `.env` queda fuera de git.
- `n8n` esta fijado por defecto en la version `2.15.0`.
- `event_hash` es el identificador idempotente de eventos. No se usa
  `event_uuid` como unico porque Cowrie puede repetirlo en varios eventos.
- El pipeline y las migraciones se ejecutan dentro de Docker; no requieren
  Python instalado en el host.
- La simulacion de descargas usa payloads inocuos servidos dentro de la red
  LAB.
