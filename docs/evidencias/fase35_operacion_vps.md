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

## Pendiente con VPS real

- Ejecutar `setup_vps.ps1` desde la PC con credenciales.
- Confirmar que Cowrie recibe conexiones reales.
- Ejecutar `sync_vps_logs.ps1 -RunPipeline`.
- Verificar datos nuevos en dashboard, sesiones, PostgreSQL, Elasticsearch y
  Telegram.
- Definir rotacion y retencion de logs en la VPS.
