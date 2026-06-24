# Fase 8 - Base LAB reproducible

## Skills utilizados

Antes de implementar se buscaron skills para:

```text
Docker Compose y contenedores
Alembic y migraciones
PowerShell
Smoke e integration testing
CI/CD
```

Se instaló y revisó:

```text
docker-expert
Fuente: davila7/claude-code-templates
```

Se reutilizó el skill local:

```text
sqlalchemy-alembic-expert-best-practices-code-review
```

Los skills de PowerShell y smoke testing encontrados no se instalaron porque tenían menor adopción y reputación insuficiente frente a la necesidad concreta.

## Cambios principales

- Pipeline Python ejecutado dentro de Docker.
- Migraciones Alembic versionadas.
- Healthchecks para servicios del LAB.
- Dependencias entre servicios basadas en salud.
- Imágenes externas fijadas por versión y digest.
- Servidor HTTP interno de payloads inocuos.
- Imagen Cowrie LAB con allowlist limitado a `payload-server`.
- Scripts de setup, validación, demo, smoke test, reset y backup.
- Eliminación de la dependencia de Python instalado en el host.
- Eliminación de la dependencia de internet durante los ataques simulados.

## Seguridad de las descargas internas

Cowrie 3.0.0 bloquea correctamente redes privadas para reducir riesgo SSRF.

No se eliminó esa protección global. La imagen derivada permite únicamente:

```text
payload-server
```

mediante:

```env
COWRIE_LAB_ALLOWED_DOWNLOAD_HOSTS=payload-server
```

La prueba produjo:

```text
cowrie.session.file_download
url=http://payload-server:8080/mirai.sh
cowrie.session.file_download
url=http://payload-server:8080/bot.sh
```

## Migraciones

Se validó Alembic sobre una base temporal completamente vacía.

Resultado:

```text
revision: 0001_initial_schema
tablas:
- alembic_version
- alerts
- eventos
- pipeline_runs
```

## Smoke test

Comando:

```powershell
.\scripts\smoke_test.ps1 -NoBuild
```

Resultado final:

```text
[validate] LAB válido
[demo] Flujo completo validado
[demo] Eventos nuevos en PostgreSQL: 106
[demo] Total acumulado: 1074
[smoke] Prueba integral superada
```

Idempotencia:

```text
Primera ejecución:
events_read=708
events_inserted=106
elasticsearch_indexed=708

Segunda ejecución:
events_read=708
events_inserted=0
elasticsearch_indexed=708
```

Estado acumulado al cierre de la validación:

```text
PostgreSQL:
- eventos: 1074
- event_hash únicos: 1074
- sesiones: 200

Elasticsearch:
- documentos: 1074
```

## Validación desde clon limpio

Se clonó el commit candidato de la Fase 8 en un directorio temporal sin `.env`, logs ni volúmenes previos y se ejecutó:

```powershell
.\scripts\smoke_test.ps1
```

Resultado:

```text
[setup] Se creó .env desde .env.example
[setup] Entorno LAB listo
[validate] LAB válido

Primera ejecución:
events_read=106
events_inserted=106
elasticsearch_indexed=106

Segunda ejecución:
events_read=106
events_inserted=0
elasticsearch_indexed=106

PostgreSQL: 106 eventos
Elasticsearch: 106 documentos
[smoke] Prueba integral superada
```

Esta prueba confirmó el flujo completo desde clon limpio, incluyendo construcción de imágenes, creación de volúmenes, migración Alembic, importación idempotente del workflow n8n, ataque offline, persistencia, indexación e idempotencia.

## Incidencias detectadas y corregidas

1. El healthcheck TCP inicial de Cowrie generaba eventos falsos en el honeypot.
   Se reemplazó por validación del proceso en `/proc/1/cmdline`.

2. Elasticsearch no refrescaba inmediatamente tras `_bulk`.
   Se agregó `refresh=wait_for`.

3. PowerShell trataba algunas salidas Docker como arreglos de líneas.
   Se normalizaron antes de comparar.

4. `setup.ps1` intentaba reimportar el workflow n8n.
   Se corrigió la comprobación para hacerla idempotente.

5. El intento original de payload interno era rechazado por la protección SSRF de Cowrie.
   Se creó un allowlist estricto para un único hostname LAB.

6. En el primer arranque Elasticsearch respondía 404 porque `cowrie-events` todavía no existía.
   El smoke test ahora interpreta exclusivamente ese 404 como un conteo inicial de cero.
