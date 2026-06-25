# Fase 21.1 - Base React y dashboard inicial

Fecha: 25 de junio de 2026.

Alcance: primeros tres objetivos de la Fase 21.

## Skills

```text
buscados:
- React TypeScript Vite TanStack Query OpenAPI ECharts dashboard testing

utilizados:
- tanstack-query
- browser:control-in-app-browser

instalados:
- tanstack-query, 340 instalaciones, revisión de seguridad sin alertas

descartados:
- alternativas TanStack Query con menor adopción
- skills React genéricos de menor alcance
```

## Implementación

```text
servicio: oscorp_frontend
imagen: oscorp/frontend:phase21
usuario: node
puerto LAB: 5173
rutas: /login y /dashboard
sesión: cookie de servidor existente
cliente API: generado desde OpenAPI
estado remoto: TanStack Query
gráficos: Apache ECharts
endpoint nuevo: GET /api/v1/analytics/timeline
```

## Validación

```text
build TypeScript/Vite: superado
pruebas frontend: 2/2
pruebas backend: 20/20
pruebas pipeline: 20/20
validación LAB: superada con frontend saludable
contenedor frontend no-root: cachés Vite/TypeScript y directorio /app verificados
login real desde navegador: superado
resumen con datos PostgreSQL: superado
timeline 24h/72h/7d: superado
distribución de riesgo: superada
errores de consola: 0
logs finales del frontend: inicio limpio, sin EACCES
```

Validación visual:

```text
desktop: 1280x720, sin solapamientos
móvil: 390x844, sin overflow horizontal
canvas desktop: 756x412 y 332x412
canvas móvil: 333x280 y 333x330
```

## Estado operativo

```text
servicios persistentes: 10
PostgreSQL / Elasticsearch: 2451 / 2451
sesiones / scores: 398 / 398
risk: 207 low, 190 medium, 1 high, 0 critical
pipeline_runs: 69
último run_id: 101
checkpoint: byte 772500, línea 1378
```

Permanecen pendientes dentro de la Fase 21 la tabla operativa de sesiones y
la ampliación sistemática de estados, accesibilidad y pruebas de componentes.
