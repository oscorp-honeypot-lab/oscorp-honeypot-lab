# Plan de arquitectura de la aplicación web

Estado: propuesta técnica previa a implementación.

Este documento define cómo se prevé construir OSCORP ThreatLab. Las versiones exactas se fijarán por versión y digest al comenzar cada fase, luego de revisar compatibilidad y seguridad.

## Enfoque

Se utilizará un monolito modular con frontend y backend separados en código, pero desplegados dentro del mismo entorno Docker Compose.

```text
Navegador
   |
Gateway HTTP del mismo origen
   |-- /          -> frontend React
   |-- /api/v1    -> backend FastAPI
   |
FastAPI
   |-- PostgreSQL
   |-- Elasticsearch, solo cuando una consulta analítica lo justifique
   |-- adaptadores de Telegram, ip-api y VirusTotal
```

No se crearán microservicios mientras el volumen, el equipo y los límites del proyecto no lo requieran. La lógica de dominio no dependerá de FastAPI, SQLAlchemy, Telegram ni proveedores externos.

## Backend

Stack previsto:

```text
Python 3.12
FastAPI
Pydantic v2 y pydantic-settings
SQLAlchemy 2 asíncrono
psycopg 3
Alembic
pytest + pytest-asyncio
HTTPX
```

Estructura prevista:

```text
backend/
├── app/
│   ├── domain/
│   │   ├── entities/
│   │   ├── value_objects/
│   │   └── ports/
│   ├── application/
│   │   ├── commands/
│   │   ├── queries/
│   │   └── services/
│   ├── adapters/
│   │   ├── persistence/
│   │   ├── notifications/
│   │   └── enrichment/
│   ├── infrastructure/
│   │   ├── config/
│   │   ├── database/
│   │   ├── logging/
│   │   └── security/
│   ├── api/
│   │   ├── dependencies/
│   │   ├── middleware/
│   │   └── v1/
│   └── main.py
└── tests/
    ├── unit/
    ├── integration/
    └── contract/
```

Reglas:

- `domain` no importa FastAPI, SQLAlchemy ni clientes externos.
- `application` coordina casos de uso mediante puertos.
- `adapters` implementa PostgreSQL, Telegram, ip-api y VirusTotal.
- `infrastructure` configura frameworks, seguridad y observabilidad.
- `api` solamente valida HTTP, aplica permisos y traduce respuestas.
- Alembic tendrá un único propietario; no existirán dos historiales de migración.

## API

La API será REST y estará versionada bajo `/api/v1`.

Convenciones previstas:

- respuestas y errores con esquemas Pydantic;
- paginación limitada y ordenamiento explícito;
- filtros representados como parámetros tipados;
- timestamps en UTC con formato ISO 8601;
- identificadores estables para sesiones, eventos, alertas y exportaciones;
- OpenAPI como contrato entre backend y frontend;
- cliente TypeScript generado para evitar divergencias manuales;
- healthchecks separados para proceso y dependencias.

PostgreSQL será la fuente de verdad operacional. Elasticsearch se reservará para búsquedas y agregaciones que realmente lo necesiten; la API no mezclará resultados incompatibles de ambas fuentes sin una regla explícita.

## Frontend

Stack previsto:

```text
React + TypeScript
Vite
React Router
TanStack Query
TanStack Table
Apache ECharts
Leaflet / React Leaflet
Lucide Icons
CSS Modules + variables CSS
Vitest + Testing Library
Playwright
```

Estructura prevista:

```text
frontend/
├── src/
│   ├── app/
│   ├── routes/
│   ├── features/
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── sessions/
│   │   ├── alerts/
│   │   ├── reports/
│   │   └── settings/
│   ├── components/
│   ├── api/
│   ├── hooks/
│   ├── styles/
│   └── test/
└── e2e/
```

La interfaz será una herramienta operativa y compacta, no una landing page. Priorizará lectura rápida, filtros persistentes, tablas estables, detalle de sesión y navegación predecible.

## Dashboards

Dashboard general:

- eventos y sesiones por período;
- sesiones por nivel de riesgo;
- IPs, usuarios, contraseñas y comandos principales;
- descargas y hashes detectados;
- MTTD y estado de alertas;
- actividad geográfica cuando el enriquecimiento esté disponible.

Vista de sesiones:

- tabla paginada y ordenable;
- filtros por fecha, IP, país, usuario, evento, score y estado de revisión;
- columnas configuradas para comparación rápida;
- acceso directo al detalle sin perder filtros.

Detalle de sesión:

- resumen e identidad de la conexión;
- timeline cronológico;
- credenciales intentadas;
- comandos ejecutados;
- archivos descargados y reputación;
- Risk Score, versión y motivos;
- alertas y MTTD;
- acción para marcar como revisada.

Los gráficos se construirán con Apache ECharts y los mapas con Leaflet. Kibana seguirá disponible como herramienta complementaria, pero la experiencia principal estará en la aplicación propia.

## Seguridad

El modo LAB seguirá enlazado por defecto a interfaces locales. Si la aplicación se publica, se utilizará HTTPS detrás del gateway.

Controles previstos:

- usuarios con roles `viewer`, `analyst` y `admin`;
- contraseñas derivadas con Argon2id;
- sesiones aleatorias almacenadas en PostgreSQL;
- cookies HttpOnly y SameSite, con Secure bajo HTTPS;
- rotación del identificador de sesión al iniciar sesión;
- expiración absoluta e inactividad;
- CSRF para acciones que cambian estado;
- CORS deshabilitado por defecto o limitado a orígenes explícitos;
- permisos verificados en backend, nunca solamente en React;
- rate limiting para login, exportaciones y consultas costosas;
- validación de tamaño, formato, rango y ordenamiento;
- cabeceras CSP, frame-ancestors, nosniff y referrer policy;
- auditoría de login, logout, revisión, exportación y administración;
- mensajes de error sin secretos ni trazas internas;
- secretos fuera del repositorio y valores inseguros prohibidos en producción.

No se almacenarán tokens de acceso ni secretos en `localStorage`.

## Pruebas

Backend:

- pruebas unitarias del dominio sin base de datos;
- pruebas de repositorios contra PostgreSQL;
- pruebas de permisos y seguridad;
- pruebas de contrato OpenAPI;
- pruebas de migración ascendente sobre base vacía y existente.

Frontend:

- pruebas de componentes y estados;
- pruebas del cliente API con respuestas controladas;
- accesibilidad básica automatizada;
- pruebas de filtros, tablas y gráficos.

End-to-end:

- login y cierre de sesión;
- apertura y filtrado del dashboard;
- detalle y revisión de una sesión;
- exportación;
- visualización de errores y expiración de sesión.

## Despliegue

Servicios previstos:

```text
web-gateway
frontend
backend
postgres
elasticsearch
kibana
n8n
cowrie
attacker-sim
payload-server
```

En producción, el frontend se compilará como archivos estáticos y el gateway servirá la interfaz y redirigirá `/api/v1` al backend. Esto evita una configuración CORS amplia y facilita cookies seguras del mismo origen.

## Referencias oficiales

- FastAPI, aplicaciones grandes: https://fastapi.tiangolo.com/tutorial/bigger-applications/
- FastAPI, seguridad: https://fastapi.tiangolo.com/tutorial/security/
- React: https://react.dev/
- Vite: https://vite.dev/guide/
- TanStack Query: https://tanstack.com/query/latest
- Apache ECharts: https://echarts.apache.org/en/index.html
- Leaflet: https://leafletjs.com/
- OWASP Password Storage Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- OWASP Session Management Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- OWASP CSRF Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
