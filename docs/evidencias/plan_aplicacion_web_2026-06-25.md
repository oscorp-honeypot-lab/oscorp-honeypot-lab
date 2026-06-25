# Evidencia de planificación de la aplicación web

Fecha: 25 de junio de 2026.

## Alcance

Se amplió el roadmap para documentar cómo se construirá OSCORP ThreatLab antes de implementar la aplicación.

Se definieron:

- backend FastAPI con arquitectura modular;
- persistencia asíncrona con SQLAlchemy 2, psycopg 3 y Alembic;
- frontend React, TypeScript y Vite;
- OpenAPI como contrato y cliente TypeScript generado;
- TanStack Query y Table para estado remoto y tablas;
- Apache ECharts y Leaflet para dashboards y mapas;
- estructura prevista de backend y frontend;
- autenticación, autorización, sesiones, CSRF, CORS y auditoría;
- estrategia de pruebas unitarias, integración y end-to-end;
- despliegue bajo un gateway del mismo origen.

La seguridad fue separada en una nueva Fase 17. Las fases posteriores fueron renumeradas hasta la Fase 39 sin reducir el alcance.

No se implementó código de la aplicación web durante esta planificación.
