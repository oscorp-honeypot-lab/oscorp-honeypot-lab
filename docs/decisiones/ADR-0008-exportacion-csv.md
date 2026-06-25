# ADR-0008 - Exportación CSV paginada

Estado: aceptado.

Fecha: 25 de junio de 2026.

## Decisión

La API exporta sesiones y eventos mediante dos endpoints autenticados:

```text
GET /api/v1/exports/sessions.csv
GET /api/v1/exports/events.csv
```

Cada solicitud produce una página independiente:

```text
page: mínimo 1
page_size: 1 a 1000
codificación: UTF-8 con BOM
fin de línea: CRLF
```

Las cabeceras `X-Export-Page`, `X-Export-Page-Size`, `X-Export-Row-Count` y
`X-Export-Total` permiten recorrer exportaciones grandes sin cargar todos los
registros en memoria.

## Seguridad

- Se aplican los mismos filtros parametrizados de la API analítica.
- No se exportan contraseñas, eventos crudos ni hashes internos.
- Las celdas que comienzan con `=`, `+`, `-` o `@` reciben un apóstrofo para
  evitar inyección de fórmulas al abrir el archivo en una hoja de cálculo.
- La lectura requiere rol `viewer` o superior.

## Trazabilidad

La tabla `app_export_runs` registra:

```text
usuario
recurso
estado
página y tamaño
filtros
filas exportadas y total
nombre y codificación
error técnico acotado
inicio y finalización
```

El archivo no se persiste en el servidor; se entrega en la respuesta HTTP.
