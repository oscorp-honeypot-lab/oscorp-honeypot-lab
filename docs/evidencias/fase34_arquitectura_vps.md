# Fase 34 - Arquitectura segura del modo REAL / VPS

## Objetivo

Preparar la base del modo REAL sin hacer que la VPS sea requisito para usar el
proyecto y sin que Codex se conecte directamente al servidor.

## Restriccion aplicada

No se intento conectar por SSH a la VPS. La recomendacion operativa queda
integrada asi:

```text
Codex versiona scripts y documentacion.
La persona con credenciales ejecuta setup_vps.ps1 manualmente desde su PC.
```

No se versionaron IPs, usuarios privados, passwords ni secretos reales.

## Arquitectura resultante

```text
Internet
   |
   v
VPS DigitalOcean / Ubuntu 24.04
   Cowrie en Docker
   /opt/oscorp-cowrie/logs/cowrie.json
   |
   | scp manual o automatizable
   v
PC local
   cowrie/logs/cowrie.json
   pipeline-worker / n8n
   PostgreSQL
   Elasticsearch
   app web
   Telegram
```

## Artefactos agregados

```text
scripts/setup_vps.ps1
scripts/sync_vps_logs.ps1
scripts/validate_real_mode.ps1
docs/arquitectura-vps.md
```

Tambien se actualizaron:

```text
.env.example
README.md
ESTADO_Y_ROADMAP.md
```

## setup_vps.ps1

Responsabilidad:

- leer `VPS_HOST`, `VPS_USER`, `VPS_SSH_PORT`, `VPS_REMOTE_DIR` y
  `VPS_COWRIE_SSH_PORT` desde `.env`, variables de entorno o parametros;
- pedir confirmacion explicita antes de tocar la VPS;
- usar `ssh` y `scp` locales;
- instalar Docker y Docker Compose v2;
- crear `/opt/oscorp-cowrie`;
- levantar `cowrie/cowrie:3.0.0`;
- publicar Cowrie en `2222` por defecto;
- no modificar el SSH administrativo de la VPS;
- configurar UFW solo de forma conservadora.

## sync_vps_logs.ps1

Responsabilidad:

- copiar el log remoto desde `VPS_COWRIE_LOG_PATH`;
- escribirlo en `cowrie/logs/cowrie.json`;
- opcionalmente ejecutar el pipeline con `-RunPipeline`.

## validate_real_mode.ps1

Responsabilidad:

- validar disponibilidad local de `ssh`, `scp` y `docker`;
- validar sintaxis de scripts PowerShell;
- validar `docker compose --profile real config`;
- confirmar que el perfil `real` no incluye `cowrie`, `attacker-sim` ni
  `payload-server`;
- confirmar que `.env.example` no define passwords de VPS.

## Seguridad

Decisiones tomadas:

- no guardar passwords de VPS en el repositorio;
- no usar `VPS_PASSWORD`;
- no exponer PostgreSQL, Elasticsearch, n8n, backend ni frontend en la VPS;
- mantener Cowrie como unico servicio publico;
- evitar puerto 22 para Cowrie en esta fase;
- ejecutar Cowrie con `no-new-privileges` y `cap_drop: ALL`.

## Limites

Esta fase no valida la VPS real porque las credenciales no estan disponibles en
el entorno de trabajo de Codex. La validacion remota queda para fase 35.

## Fase siguiente

Fase 35 debe:

- ejecutar `setup_vps.ps1` contra la VPS real;
- generar o esperar trafico SSH real;
- sincronizar logs;
- procesar eventos con `sync_vps_logs.ps1 -RunPipeline`;
- verificar app web, PostgreSQL, Elasticsearch y Telegram;
- automatizar sincronizacion con reintentos y evidencia.
