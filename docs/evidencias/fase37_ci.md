# Fase 37 — Pruebas automatizadas y CI

**Fecha:** 2026-06-27
**Estado:** Completada

## Objetivo

Establecer controles continuos de calidad: lint Python, type-check TypeScript,
tests unitarios e integración en GitHub Actions, y una línea base de cobertura.

## Cambios implementados

### 1. Lint Python — ruff

Configurado en `ruff.toml` (raíz del proyecto):

| Reglas activas | Descripción |
|---|---|
| `E4`, `E7`, `E9` | Errores críticos de sintaxis y estilo (pycodestyle) |
| `F` | Pyflakes: imports no usados, nombres no definidos |
| `I` | Isort: orden de imports por sección (stdlib → terceros → first-party) |

`known-first-party` configurados: `app`, `process_cowrie_ndjson`, `pipeline_worker`,
`risk`, `geo`, `vt`, `alerts`, `reports`, `contracts`.

Las migraciones (`pipeline/migrations/versions/*.py`) tienen `I001` excluido porque
el orden de imports en archivos Alembic no es relevante.

**81 violaciones corregidas automáticamente** con `ruff check --fix` antes de
habilitar el job de CI.

### 2. Fix en `SessionDetailPage.test.tsx`

Agregado `source_mode: "lab"` a `baseSession` en el test fixture. La omisión
causaba un error de TypeScript en tiempo de compilación después de la Fase 36,
porque `SessionListItemResponse` pasó a requerir el campo obligatorio `source_mode`.

### 3. `pytest-cov` en backend

Agregado `pytest-cov==6.2.1` a `backend/requirements.txt`. Se usa en el job de
integración de CI para medir cobertura sobre el paquete `app` con línea base
de **60 %** (`--cov-fail-under=60`).

### 4. GitHub Actions CI — `.github/workflows/ci.yml`

Pipeline en 6 jobs independientes que corren en paralelo:

| Job | Runner | Descripción |
|---|---|---|
| `validate-compose` | ubuntu-latest | `docker compose config --quiet` para profiles `lab` y `real` |
| `lint-python` | ubuntu-latest | `ruff check` sobre backend, pipeline y scripts |
| `typecheck-frontend` | ubuntu-latest | `npx tsc --noEmit` |
| `test-frontend` | ubuntu-latest | `npm test` (vitest) |
| `test-pipeline` | ubuntu-latest | `python -m unittest discover` (no DB) |
| `test-backend-unit` | ubuntu-latest | `pytest tests/unit tests/contract` (no DB) |
| `test-backend-integration` | ubuntu-latest | `pytest tests/integration` + postgres service |

#### Diseño sin secretos reales

El job de integración usa credenciales de CI ficticias:

```yaml
OSCORP_API_ADMIN_PASSWORD: CiTestPassword2026!
OSCORP_API_DATABASE_URL: postgresql+psycopg://oscorp:oscorp_ci@localhost:5432/oscorp
```

No se usan ni exponen: VPS_HOST, VPS_USER, TELEGRAM_BOT_TOKEN, VT_API_KEY,
ni ningún secreto de producción.

#### Migraciones en CI

El job de integración instala `pipeline/requirements.txt` (que incluye alembic)
y ejecuta `python -m alembic upgrade head` contra el servicio postgres de GitHub Actions
antes de correr los tests del backend.

#### PYTHONPATH para pipeline

Los tests de pipeline importan `process_cowrie_ndjson` (en `scripts/`) y módulos
internos como `risk`, `geo`, `vt` (en `pipeline/`). El CI configura:

```yaml
PYTHONPATH: ${{ github.workspace }}/scripts
```

`pipeline/` se agrega automáticamente a `sys.path` via `python -m unittest discover`.

## Pruebas ejecutadas

### Ruff — lint Python

```
python -m ruff check backend/app backend/tests scripts/process_cowrie_ndjson.py pipeline/
All checks passed!
```

### Frontend — TypeScript + vitest

```
npx tsc --noEmit → sin errores (incluye source_mode: string en tipos generados)
```

Nota: `vitest run` se ejecuta dentro del contenedor `oscorp_frontend` o localmente
con `npm test` en `frontend/`.

### Docker Compose — validación de sintaxis

```
docker compose --profile lab config --quiet   → válido
docker compose --profile real config --quiet  → válido
```

## Cobertura — línea base

La cobertura se mide sobre `app/` del backend en el job de integración.
Línea base establecida: **60 %** de cobertura de ramas.

Los 3 tests pre-existentes con error en `test_reports_api.py` (constraint
`uq_report_runs_period`) no afectan la cobertura: son fallos conocidos de
concurrencia con el LAB corriendo en paralelo, y se reportan como tales.

## Estructura de archivos

```
.github/
  workflows/
    ci.yml                        ← pipeline completo en 6 jobs
ruff.toml                         ← configuración de linting Python
backend/requirements.txt          ← agregado pytest-cov==6.2.1
frontend/src/features/sessions/
  SessionDetailPage.test.tsx      ← fix: source_mode: "lab" en baseSession
```
