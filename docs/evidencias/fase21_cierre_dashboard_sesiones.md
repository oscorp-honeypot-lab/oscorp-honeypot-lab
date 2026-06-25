# Fase 21 - Cierre del dashboard y sesiones

Fecha: 25 de junio de 2026.

## Alcance

```text
[x] tabla de sesiones con TanStack Table
[x] filtros por IP, país, usuario, riesgo y revisión
[x] paginación de servidor con 25, 50 y 100 filas
[x] ordenamiento de servidor con lista blanca
[x] estados de carga, vacío, error y actualización
[x] accesibilidad y comportamiento responsive
```

## Skills

```text
buscados:
- TanStack Table React accessibility testing

utilizados:
- tanstack-query
- tanstack-table
- browser:control-in-app-browser

instalados:
- tanstack-table, 2.6K instalaciones
- evaluación: Safe, 0 alertas, Low Risk
```

## Validación

```text
build TypeScript/Vite: superado
pruebas frontend: 5/5
pruebas backend: 21/21
pruebas pipeline: 20/20
validación LAB: superada con 10 servicios persistentes
Docker Compose: válido
```

Validación funcional en navegador:

```text
sesiones totales: 398
filas iniciales: 25
páginas: 16
ordenamiento event_count desc: verificado
filtro risk_level=high: 1 resultado, score 60
estado vacío con IP inexistente: verificado
navegación a página 2: verificada
consola: 0 errores
```

Validación responsive:

```text
desktop: sin overflow global
móvil: viewport solicitado 390x844
ancho de contenido efectivo: 375 px
overflow global: no
tabla: scroll horizontal interno 980/346 px
filtros: una columna en móvil
```

## Estado operativo

```text
eventos PostgreSQL: 2451
sesiones: 398
scores: 398
risk: 207 low, 190 medium, 1 high, 0 critical
pipeline_runs: 69
último run_id: 101
```

La Fase 21 queda completa. El siguiente trabajo corresponde a la Fase 22:
detalle interactivo de sesión.
