# Fase 9 - Contrato entre n8n y el pipeline

Fecha: 25 de junio de 2026.

## Skills

Se buscaron Skills para:

```text
n8n workflow integration
n8n credentials docker compose
```

Se instalaron y revisaron:

```text
n8n-workflow
Fuente: claude-office-skills/skills
Adopción observada: aproximadamente 3000 instalaciones
Evaluación automática: Safe, 0 alerts, Low Risk

n8n-credentials-and-security
Fuente oficial: n8n-io/skills
Evaluación automática: Safe, 0 alerts
```

También se utilizó `architecture-patterns` para separar orquestación, worker e infraestructura.

## Decisión

Se aceptó `ADR-0001`:

```text
n8n = orquestador
Python = worker autoritativo
scripts/run_pipeline.ps1 = entrada de recuperación al mismo worker
```

El workflow no vuelve a implementar el parser, no construye SQL y no contiene secretos.

## Contratos

Se agregaron:

```text
pipeline/contracts/run-request.schema.json
pipeline/contracts/run-result.schema.json
```

Ambos utilizan la versión de contrato `1.0`.

La adaptación del worker para aceptar la solicitud y emitir el resultado JSON queda reservada para la Fase 10.

## Credenciales

Se configuraron credenciales nativas con IDs estables:

```text
oscorp-postgres
oscorp-elasticsearch
```

Los valores se generan temporalmente desde `.env`, se importan mediante la CLI y se cifran dentro de n8n. El archivo temporal se elimina al finalizar.

`setup.ps1`:

- genera una clave local de 256 bits si no existe;
- recupera la clave del volumen en instalaciones previas;
- evita reemplazar una clave que ya protege datos;
- sincroniza credenciales y workflow de forma idempotente.

La exportación de control confirmó que el campo `data` de ambas credenciales permanece cifrado.

## Workflow

El workflow versionado de Fase 9:

```text
OSCORP - Pipeline Contract Check
id: oscorp-cowrie-ndjson-pipeline
estado: inactivo
disparador: manual
```

Realiza solamente:

1. consulta de lectura a PostgreSQL;
2. consulta de salud a Elasticsearch.

Resultado observado:

```text
PostgreSQL:
- database_name: oscorp
- database_user: oscorp
- event_count: 1074 en la primera validación

Elasticsearch:
- cluster_name: docker-cluster
- status: yellow
- timed_out: false

Workflow:
- status: success
- lastNodeExecuted: Check Elasticsearch Credential
```

## Validaciones

Comandos:

```powershell
.\scripts\setup.ps1 -NoBuild
.\scripts\validate_n8n_contract.ps1
.\scripts\smoke_test.ps1 -NoBuild
.\scripts\validate_n8n_contract.ps1
```

Resultados:

```text
- importación idempotente de 2 credenciales;
- workflow sincronizado por ID estable;
- workflow manual ejecutado correctamente;
- credenciales exportadas únicamente en forma cifrada;
- archivo temporal de credenciales eliminado;
- smoke test integral superado;
- segunda ingesta del pipeline sin duplicados;
- siete servicios LAB saludables al finalizar.
```

Durante el smoke test se corrigió una carrera heredada: `run_demo.ps1` ahora espera hasta 15 segundos a que Cowrie escriba eventos nuevos antes de declarar un fallo.

## Estado operativo final

```text
PostgreSQL:
- eventos: 1286
- event_hash únicos: 1286
- sesiones: 230
- pipeline_runs: 16
- último evento: 2026-06-25 01:17:00.050016

Elasticsearch:
- documentos: 1286

n8n:
- versión: 2.15.0
- credenciales cifradas: 2
- workflow de contrato: validado e inactivo
```

## Validación desde clon limpio

Se clonó el commit candidato en un directorio temporal sin `.env` ni volúmenes previos.

Resultado:

```text
setup.ps1:
- creó .env;
- generó una clave de cifrado local;
- importó 2 credenciales;
- importó el workflow por ID estable.

validate_n8n_contract.ps1:
- contratos válidos;
- credenciales exportadas cifradas;
- PostgreSQL accesible desde n8n;
- Elasticsearch accesible desde n8n;
- workflow finalizado con status success.

smoke_test.ps1:
- 106 eventos en PostgreSQL;
- 106 documentos en Elasticsearch;
- 15 sesiones;
- 2 registros en pipeline_runs;
- segunda ingesta con 0 duplicados.

Seguridad:
- clave local configurada;
- archivo temporal de credenciales ausente al finalizar.
```
