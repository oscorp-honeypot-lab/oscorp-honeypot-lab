# ADR-0007 - Filtros y revisión operativa

Estado: aceptado.

Fecha: 25 de junio de 2026.

## Decisión

La consulta de sesiones admite filtros combinables por rango temporal, IP,
país, usuario, tipo de evento, criticidad y estado de revisión. La consulta de
eventos admite los filtros aplicables a eventos individuales.

Los valores se envían como parámetros enlazados a PostgreSQL. La composición
dinámica se limita a cláusulas SQL predefinidas.

## País

El país se lee de campos de enriquecimiento compatibles dentro de
`eventos.raw_event`:

```text
country
country_name
geo.country
geo.country_name
geoip.country
geoip.country_name
```

El filtro queda disponible antes de implementar el enriquecimiento. En datos
LAB sin país devuelve cero coincidencias.

## Revisión

```text
endpoint: PATCH /api/v1/sessions/{session_key}/review
rol mínimo: analyst
protección: sesión de servidor y CSRF
estado: reviewed
trazabilidad: reviewed_at y reviewed_by
auditoría: app_audit_log, acción session.review
```

Desmarcar una sesión limpia fecha y actor actuales, pero conserva la
transición histórica en auditoría.
