# Fase 18 - API de consulta analítica

Fecha: 25 de junio de 2026.

## Skills

```text
buscados:
- FastAPI analytics API pagination SQLAlchemy PostgreSQL integration testing

utilizados:
- fastapi-templates
- architecture-patterns
- sqlalchemy-alembic-expert-best-practices-code-review
- python-expert-best-practices-code-review

instalados: ninguno
descartados:
- skills externos de FastAPI y paginación redundantes con los disponibles
```

## Implementación

```text
GET /api/v1/analytics/summary
GET /api/v1/sessions?page=1&page_size=50
GET /api/v1/events?page=1&page_size=50
GET /api/v1/sessions/{session_key}
rol mínimo: viewer
paginación máxima: 100
score activo: 1.0.0
contraseñas y raw_event: no expuestos
migraciones nuevas: ninguna
```

El módulo mantiene las capas `domain`, `application`, `ports`, adaptador
PostgreSQL y API FastAPI.

## Validación

```text
pruebas backend: 15/15
pruebas pipeline: 20/20
OpenAPI: cuatro contratos analíticos presentes
autenticación: requerida en todos los endpoints
rol viewer: lectura permitida
resumen: contrastado contra PostgreSQL
paginación: límites y totales verificados
detalle: comandos, descargas, score y eventos verificados
privacidad: password y raw_event ausentes
sesión inexistente: 404
smoke integral: superado
segunda ingesta: 0 eventos
```

## Estado operativo

```text
PostgreSQL: 2241 eventos
Elasticsearch: 2241 documentos
sesiones / scores: 368 / 368
IPs fuente únicas: 7
sesiones con login exitoso: 211
sesiones con descarga: 21
risk: 195 low, 172 medium, 1 high, 0 critical
pipeline_runs: 63
último run_id: 95
checkpoint: byte 654101, línea 1168
```

## Reproducibilidad desde clon limpio

```text
commit candidato: 13a2719
estado inicial: sin .env y con volúmenes Docker vacíos
migración: 0006_identity_security en head
pruebas backend: 15/15
pruebas pipeline: 20/20
eventos: 105
sesiones / scores: 15 / 15
risk: 6 low, 9 medium, 0 high, 0 critical
administradores activos: 1
checkpoint: byte 59200, línea 105
segunda ingesta: 0 eventos
resultado: smoke integral superado
```
