# Fase 35 - Operacion REAL y sincronizacion continua de VPS

## Objetivo

Convertir la base segura de Fase 34 en un flujo operativo para iniciar el modo
REAL, traer eventos desde la VPS y procesarlos con el pipeline local.

## Alcance implementado

No se realizo conexion SSH a la VPS desde Codex. La fase implementa la
automatizacion local y deja la validacion remota para la persona que tiene las
credenciales.

## Artefactos agregados o modificados

```text
scripts/setup_real.ps1
scripts/run_real_sync.ps1
scripts/run_n8n_pipeline.ps1
scripts/sync_vps_logs.ps1
scripts/validate_real_mode.ps1
README.md
docs/arquitectura-vps.md
ESTADO_Y_ROADMAP.md
```

## setup_real.ps1

Responsabilidad:

- crear `.env` desde `.env.example` si falta;
- generar `N8N_ENCRYPTION_KEY` si falta;
- generar `OSCORP_API_ADMIN_PASSWORD` si falta;
- validar `docker compose --profile real config`;
- levantar el perfil `real`;
- inicializar el usuario administrador;
- importar credenciales y workflow n8n.

El script acepta:

```powershell
.\scripts\setup_real.ps1
.\scripts\setup_real.ps1 -NoBuild
.\scripts\setup_real.ps1 -ValidateOnly
```

## run_real_sync.ps1

Responsabilidad:

- ejecutar `sync_vps_logs.ps1`;
- ejecutar el pipeline con perfil `real`;
- reintentar fallos transitorios;
- dejar evidencia local en `logs/real-sync/`;
- permitir modo continuo o una sola corrida.

Ejemplos:

```powershell
.\scripts\run_real_sync.ps1
.\scripts\run_real_sync.ps1 -Once
.\scripts\run_real_sync.ps1 -IntervalSeconds 60
.\scripts\run_real_sync.ps1 -NoPipeline
```

## run_n8n_pipeline.ps1

Se parametrizo el perfil:

```powershell
.\scripts\run_n8n_pipeline.ps1 -Profile lab
.\scripts\run_n8n_pipeline.ps1 -Profile real
```

El default sigue siendo `lab`, para no romper scripts existentes.

## Flujo operativo esperado

Primera vez:

```powershell
.\scripts\setup_vps.ps1
.\scripts\setup_real.ps1
.\scripts\sync_vps_logs.ps1 -RunPipeline
```

Uso sostenido:

```powershell
.\scripts\setup_real.ps1 -NoBuild
.\scripts\run_real_sync.ps1
```

## Validacion local

Validacion sin tocar la VPS:

```powershell
.\scripts\validate_real_mode.ps1
.\scripts\setup_real.ps1 -ValidateOnly
```

## Validacion con VPS real

- `setup_vps.ps1` fue ejecutado desde la PC con credenciales.
- Cowrie recibio conexiones reales en la VPS de DigitalOcean.
- `sync_vps_logs.ps1 -RunPipeline` proceso datos con perfil `real`.
- Se validaron datos REAL en app, PostgreSQL, Elasticsearch y Telegram.
- La evidencia operativa registra 331 sesiones REAL capturadas.

## Rotacion, retencion y apagado

Politica definida para el sensor VPS:

- El log remoto autoritativo es `/opt/oscorp-cowrie/logs/cowrie.json`.
- Antes de rotar o apagar la VPS se debe ejecutar una ultima sincronizacion:
  `.\scripts\sync_vps_logs.ps1 -RunPipeline`.
- Retener logs crudos en la VPS por 7 dias como ventana operativa corta.
- Conservar respaldos/exportaciones locales fuera de git; `backups/*` y
  `cowrie/logs/*` permanecen ignorados.
- Si se requiere una ventana mayor de investigacion, exportar primero desde
  PostgreSQL/Elasticsearch o crear backup local con `scripts/backup.ps1`.

Procedimiento de apagado recomendado:

1. Ejecutar `.\scripts\sync_vps_logs.ps1 -RunPipeline`.
2. Verificar sesiones REAL en la app con el filtro de modo.
3. En la VPS, detener Cowrie desde `VPS_REMOTE_DIR` con
   `docker compose down`.
4. Guardar evidencia local necesaria y apagar o destruir la VPS desde el panel
   del proveedor para evitar costos.

## Evaluacion de SSH por clave

Decision: migrar a una clave SSH dedicada es recomendado para uso sostenido,
pero no se automatiza desde Codex para evitar bloqueo accidental de acceso.

Criterio operativo:

- Usar una clave Ed25519 dedicada y con passphrase, generada fuera del repo.
- Versionar solo instrucciones; nunca claves privadas, passwords ni `VPS_PASSWORD`.
- Probar login por clave en una segunda terminal antes de deshabilitar password.
- Mantener `ssh`/`scp` como mecanismo de autenticacion externo al proyecto.
