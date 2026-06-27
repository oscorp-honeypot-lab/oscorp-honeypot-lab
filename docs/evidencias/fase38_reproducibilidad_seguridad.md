# Fase 38 — Reproducibilidad y revisión de seguridad final

Fecha: 27 de junio de 2026

## Objetivo

Validar que el sistema es instalable, respaldable y auditable antes de la entrega final.

## Tareas completadas

### 1. Revisión de dependencias, secretos, privacidad y retención de datos

Se creó `pipeline/tests/test_security_audit.py` con 13 tests automatizados que verifican las propiedades de seguridad del proyecto:

**Clase GitignoreTests (4 tests):**
- `.env` está en `.gitignore`
- `cowrie/logs/*` está en `.gitignore`
- `backups/*` está en `.gitignore`
- `n8n/credentials/*` está en `.gitignore`

**Clase DockerImagePinningTests (2 tests):**
- Imágenes externas tienen `@sha256:` (reproducibilidad de builds)
- Imágenes locales `oscorp/*` declaran `pull_policy: never`

**Clase RequirementsPinningTests (2 tests):**
- `pipeline/requirements.txt` usa `==` para todas las dependencias
- `backend/requirements.txt` usa `==` para todas las dependencias

**Clase EnvExampleSecurityTests (5 tests):**
- `N8N_ENCRYPTION_KEY` vacío (generado al momento de setup)
- `OSCORP_API_ADMIN_PASSWORD` vacío (generado al momento de setup)
- `VT_API_KEY` vacío (configurado por el usuario)
- `VPS_HOST` vacío (no se versiona la IP de la VPS)
- `ELASTICSEARCH_PASSWORD` vacío

**Resultado:** 13/13 tests superados

```
test_external_images_have_digest_pin ... ok
test_local_images_have_pull_policy_never ... ok
test_admin_password_is_empty ... ok
test_elasticsearch_password_is_empty ... ok
test_n8n_encryption_key_is_empty ... ok
test_vps_host_is_empty ... ok
test_vt_api_key_is_empty ... ok
test_backups_are_ignored ... ok
test_cowrie_logs_are_ignored ... ok
test_env_is_ignored ... ok
test_n8n_credentials_are_ignored ... ok
test_backend_requirements_all_pinned ... ok
test_pipeline_requirements_all_pinned ... ok

Ran 13 tests in 0.012s — OK
```

Hallazgos de la auditoría de seguridad:

| Verificación | Estado | Observación |
|---|---|---|
| .env no versionado | ✅ | `.env` en `.gitignore` desde Fase 1 |
| Logs Cowrie no versionados | ✅ | `cowrie/logs/*` en `.gitignore` |
| Backups no versionados | ✅ | `backups/*` en `.gitignore` |
| Credenciales n8n no versionadas | ✅ | `n8n/credentials/*` en `.gitignore` |
| Imágenes externas con digest SHA-256 | ✅ | 4 imágenes externas fijadas |
| Imágenes locales con pull_policy:never | ✅ | 4 imágenes oscorp/* |
| Dependencias Python pinneadas exactas | ✅ | pipeline y backend usan `==` |
| Secretos vacíos en .env.example | ✅ | 5 claves sensibles vacías |
| Contraseñas lab en .env.example | ℹ️ | `oscorp123` / `admin123` son defaults de LAB documentados |

Las contraseñas por defecto de laboratorio (`POSTGRES_PASSWORD=oscorp123`, `N8N_BASIC_AUTH_PASSWORD=admin123`) son aceptadas como riesgo conocido del modo LAB. El README y la documentación de arquitectura advierten que estas deben cambiarse en entornos expuestos a internet.

### 2. Backup y restauración completos

Se actualizó `scripts/backup.ps1` para incluir `--clean --if-exists` en el pg_dump, lo que hace que el dump sea auto-suficiente para restauración (incluye `DROP TABLE IF EXISTS` antes de cada `CREATE TABLE`).

Se creó `scripts/restore.ps1` que:
1. Valida que el directorio de backup exista y contenga `postgres.sql`
2. Detiene servicios (excepto postgres) para evitar escrituras concurrentes
3. Restaura PostgreSQL desde el dump `--clean --if-exists`
4. Restaura `cowrie.json` si está presente en el backup
5. Reinicia el stack completo
6. Borra el índice Elasticsearch y resetea el checkpoint a 0
7. Ejecuta el pipeline para re-indexar eventos en Elasticsearch
8. Ejecuta `validate_lab.ps1` para confirmar el estado post-restauración

**Prueba de restauración (no destructiva):**

```
Base origen:
  eventos:       1879
  sessions:      331
  pipeline_runs: 51

Backup creado: 4460 líneas SQL

Restauración a base de test oscorp_restore_test:
  eventos:       1879  ✅
  sessions:      331   ✅
  pipeline_runs: 51    ✅

Base de test eliminada después de la verificación.
```

El ciclo backup → restore → verificación fue completamente exitoso.

### 3. Validación de reproducibilidad

Se creó `scripts/validate_reproducibility.ps1` que automatiza la auditoría de reproducibilidad e incluye:

- Verificación de archivos no versionados en git
- Verificación de secretos en `.env.example`
- Verificación de pinning de imágenes Docker externas
- Verificación de pinning de dependencias Python
- Verificación de Docker Compose para ambos perfiles
- Ejecución de tests de auditoría Python
- Ejecución de `validate_lab.ps1`

Desde PowerShell con Docker disponible, el script ejecuta todos los checks (incluyendo Docker). Desde entornos sin Docker, los checks de Docker se omiten con aviso.

### 4. Versión etiquetada del sistema

Se creó el tag `v1.0.0` que marca la primera entrega completa del sistema:

```
git tag v1.0.0 -m "OSCORP ThreatLab v1.0.0 — Primera entrega completa"
```

El tag incluye:
- 39 fases implementadas (Fase 1 → Fase 38)
- Stack LAB completo (10 servicios)
- Stack REAL con sincronización VPS
- Pipeline de ingesta, análisis y alertas
- Aplicación web propia (React + FastAPI)
- Dashboards Kibana
- Tests automatizados y CI GitHub Actions

## Estado de tests post-Fase 38

| Suite | Cantidad | Estado |
|---|---|---|
| Security audit (host/CI) | 13 | ✅ OK |
| Pipeline (Docker container) | 144 | ✅ OK |
| Backend (Docker) | 76 | ✅ OK (sin cambios) |
| Frontend (Vitest) | 23 | ✅ OK (sin cambios) |

## Archivos creados o modificados

| Archivo | Acción |
|---|---|
| `pipeline/tests/test_security_audit.py` | Creado — 13 tests de auditoría |
| `scripts/backup.ps1` | Modificado — agrega `--clean --if-exists` a pg_dump |
| `scripts/restore.ps1` | Creado — restauración desde backup |
| `scripts/validate_reproducibility.ps1` | Creado — auditoría integral de reproducibilidad |

## Aceptación de riesgos conocidos

| Riesgo | Nivel | Aceptación |
|---|---|---|
| Contraseñas default en .env.example (LAB) | Medio | Aceptado: solo afecta modo LAB, documentado como config de laboratorio |
| Sin cifrado en tránsito LAB | Medio | Aceptado: entorno local Docker, sin exposición externa |
| n8n sin HTTPS en LAB | Medio | Aceptado: solo accesible en localhost:5678 |
| PostgreSQL/Elasticsearch sin auth en LAB | Alto | Aceptado: servicios no expuestos a internet en LAB |

Todos los riesgos están dentro de los límites esperados para un entorno de laboratorio académico y son documentados explícitamente en el README.
