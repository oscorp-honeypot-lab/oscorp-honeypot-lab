# ADR-0009 - Frontend React y dashboard inicial

Estado: aceptado.

Fecha: 25 de junio de 2026.

## Decisión

La aplicación web utiliza:

```text
React 19.2.7
TypeScript 6.0.3
Vite 8.1.0
React Router 7.18.0
TanStack Query 5.101.1
Apache ECharts 6.1.0
Lucide React 1.21.0
```

El frontend se ejecuta como servicio Docker no-root y Vite redirige `/api`
al backend. De este modo las cookies de sesión permanecen en el mismo origen
durante el modo LAB.

## Contrato API

El cliente TypeScript se genera desde `/openapi.json` mediante
`@hey-api/openapi-ts`. Los tipos y funciones generados se versionan para que
el build sea reproducible y para detectar divergencias mediante TypeScript.

TanStack Query administra exclusivamente estado remoto:

```text
auth/me
analytics/summary
analytics/timeline/{hours}
```

No se almacenan tokens ni secretos en `localStorage`.

## Dashboard

El dashboard inicial incluye:

- cinco métricas operativas;
- evolución horaria de eventos y sesiones;
- selector de 24 horas, 72 horas y 7 días;
- distribución del Attack Risk Score;
- último evento y sesiones de riesgo alto o crítico.

La evolución temporal se calcula en PostgreSQL mediante un endpoint dedicado.
El navegador no reconstruye estadísticas a partir de páginas incompletas.
