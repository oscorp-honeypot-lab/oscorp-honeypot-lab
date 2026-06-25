# ADR-0004 - Arquitectura del backend FastAPI

Estado: aceptado.

Fecha: 25 de junio de 2026.

## Decisión

El backend se implementa como monolito modular con dependencias orientadas
hacia el dominio:

```text
api -> application -> domain
adapters -> domain
infrastructure -> adapters y framework
```

`domain` no importa FastAPI, SQLAlchemy ni Pydantic. La API valida HTTP y
traduce respuestas; los adaptadores encapsulan PostgreSQL.

## Stack fijado

```text
Python 3.12.4
FastAPI 0.138.1
Pydantic 2.13.4
pydantic-settings 2.14.2
SQLAlchemy 2.0.51
psycopg 3.3.4
Uvicorn 0.49.0
structlog 26.1.0
pytest 9.1.1
```

## Migraciones

El backend no crea un historial Alembic propio. La única cadena permanece en
`pipeline/migrations`, actualmente en `0005_session_risk_scores`.

## Operación

```text
GET /api/v1/health/live
GET /api/v1/health/ready
GET /openapi.json
GET /docs
```

El contenedor ejecuta Uvicorn como UID 10002. Los logs de aplicación se
emiten como JSON y cada respuesta incluye `x-request-id`.
