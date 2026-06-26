# Arquitectura REAL / VPS

El modo REAL permite capturar trafico SSH real desde una VPS publica sin volver
obligatoria la VPS para probar el proyecto. El LAB local sigue siendo la ruta
principal y reproducible; la VPS funciona como sensor externo opcional.

## Regla operativa

Codex no debe conectarse por SSH a la VPS. La configuracion remota se entrega
como script versionado y la ejecuta manualmente la persona que tiene las
credenciales.

```text
PC local
  scripts/setup_vps.ps1 --usa ssh/scp--> VPS

VPS publica
  Docker + Cowrie -> /opt/oscorp-cowrie/logs/cowrie.json

PC local
  scripts/sync_vps_logs.ps1 -> cowrie/logs/cowrie.json
  scripts/run_real_sync.ps1 -> sincronizacion periodica
  scripts/run_n8n_pipeline.ps1
  PostgreSQL / Elasticsearch / app web / Telegram
```

## Separacion LAB y REAL

Modo LAB:

```text
attacker-sim -> Cowrie local -> cowrie/logs/cowrie.json -> pipeline
```

Modo REAL:

```text
internet -> Cowrie en VPS -> scp -> cowrie/logs/cowrie.json -> pipeline
```

El perfil `real` de Docker Compose levanta el stack de procesamiento local sin
`cowrie`, `attacker-sim` ni `payload-server`. El origen de eventos se sincroniza
desde la VPS.

## Variables

No se versionan passwords de VPS. La autenticacion queda en manos de OpenSSH:
si se usa password, `ssh` o `scp` la piden interactivamente; si se usa clave,
OpenSSH usa la clave configurada en la maquina local.

```env
VPS_HOST=
VPS_USER=root
VPS_SSH_PORT=22
VPS_REMOTE_DIR=/opt/oscorp-cowrie
VPS_COWRIE_SSH_PORT=2222
VPS_COWRIE_LOG_PATH=/opt/oscorp-cowrie/logs/cowrie.json
```

## Configuracion inicial de la VPS

Desde la raiz del proyecto, en la PC de quien tiene credenciales:

```powershell
.\scripts\setup_vps.ps1
```

Tambien se pueden pasar parametros sin editar `.env`:

```powershell
.\scripts\setup_vps.ps1 -Host "IP_DE_LA_VPS" -User root -SshPort 22 -CowriePort 2222
```

El script:

- verifica `ssh` y `scp` locales;
- pide confirmacion explicita antes de tocar la VPS;
- instala Docker y Docker Compose v2 en Ubuntu;
- crea `/opt/oscorp-cowrie`;
- levanta `cowrie/cowrie:3.0.0` con un compose minimo;
- publica Cowrie en el puerto `2222` por defecto;
- no cambia el SSH administrativo de la VPS;
- agrega reglas UFW si UFW existe, pero no habilita UFW si estaba apagado;
- valida que el contenedor quede en ejecucion.

## Sincronizacion de logs

Cuando Cowrie ya esta corriendo en la VPS:

```powershell
.\scripts\sync_vps_logs.ps1
```

Para sincronizar y procesar en un solo paso:

```powershell
.\scripts\sync_vps_logs.ps1 -RunPipeline
```

El script copia el `cowrie.json` remoto hacia:

```text
cowrie/logs/cowrie.json
```

Luego el pipeline local procesa ese archivo igual que en LAB. Si el archivo se
reemplaza o rota, el checkpoint incremental detecta el cambio y la idempotencia
por `event_hash` evita duplicados persistidos.

## Operacion local del modo REAL

Para levantar el stack local que procesa los eventos de la VPS:

```powershell
.\scripts\setup_real.ps1
```

Este script prepara `.env`, levanta `docker compose --profile real`, inicializa
la identidad administrativa y sincroniza credenciales/workflow n8n.

Para una ejecucion continua con reintentos:

```powershell
.\scripts\run_real_sync.ps1
```

Por defecto ejecuta:

```text
scp VPS:cowrie.json -> cowrie/logs/cowrie.json
run_n8n_pipeline.ps1 -Profile real
```

y deja logs locales en `logs/real-sync/`.

## Endurecimiento inicial

La fase 34 deja una base prudente, no un hardening final:

- Cowrie se expone en `2222`, no en `22`, para no interferir con el SSH real.
- Solo Cowrie queda expuesto publicamente en la VPS.
- PostgreSQL, Elasticsearch, n8n, backend y frontend siguen locales.
- No se guardan passwords de VPS en `.env.example`, README, roadmap ni scripts.
- El contenedor Cowrie corre con `no-new-privileges` y `cap_drop: ALL`.
- La VPS debe considerarse host expuesto: revisar costos, logs y seguridad antes
  de dejarla activa mucho tiempo.

## Validacion local

Sin conectarse a ninguna VPS:

```powershell
.\scripts\validate_real_mode.ps1
```

Esta validacion comprueba:

- disponibilidad local de `ssh`, `scp` y `docker`;
- sintaxis de scripts PowerShell;
- validez del perfil `real` de Docker Compose;
- ausencia de `cowrie`, `attacker-sim` y `payload-server` en el perfil `real`;
- ausencia de variables de password de VPS en `.env.example`.

## Pendiente para fase 35

- Ejecutar `setup_vps.ps1` contra la VPS real de DigitalOcean.
- Probar exposicion publica de Cowrie con eventos reales controlados.
- Definir rotacion/retencion de logs en VPS.
- Evaluar si conviene migrar de password SSH a clave SSH.
