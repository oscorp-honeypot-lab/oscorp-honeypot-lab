# ADR-0001: contrato entre n8n y el pipeline

Estado: aceptado.

Fecha: 25 de junio de 2026.

## Contexto

El workflow heredado leía todo el NDJSON, repetía la normalización en JavaScript, construía SQL mediante expresiones y enviaba cada evento directamente a PostgreSQL y Elasticsearch.

La Fase 8 ya consolidó un procesador Python contenerizado que:

- normaliza eventos;
- usa SQL parametrizado;
- evita duplicados mediante `event_hash`;
- indexa por lotes;
- registra ejecuciones en `pipeline_runs`;
- funciona sin Python instalado en el host.

Mantener ambos procesadores produciría reglas divergentes y duplicaría correcciones.

## Decisión

n8n será el orquestador y el procesador Python será el worker autoritativo.

```text
n8n
  -> crea una solicitud de ejecución
  -> invoca al worker
  -> recibe un resultado estructurado
  -> decide éxito, reintento o alerta

worker Python
  -> lee Cowrie NDJSON
  -> normaliza
  -> persiste en PostgreSQL
  -> indexa en Elasticsearch
  -> registra pipeline_runs
  -> devuelve métricas y estado
```

El script manual continuará disponible como mecanismo de recuperación, ejecutando el mismo worker y no una implementación alternativa.

## Contratos

Los contratos versionados son:

```text
pipeline/contracts/run-request.schema.json
pipeline/contracts/run-result.schema.json
```

La versión inicial es `1.0`.

Entradas principales:

- `request_id`: UUID de correlación generado por n8n;
- `triggered_by`: disparador manual, programado o recuperación;
- `mode`: incremental o recuperación;
- `source`: identificador lógico, nunca una ruta arbitraria provista por el usuario.

Salidas principales:

- `run_id`;
- `status`;
- `events_read`;
- `events_inserted`;
- `events_indexed`;
- `errors_count`;
- `error_code` y `error_detail`.

## Códigos de salida previstos

```text
0  ejecución completada
2  configuración inválida
3  fuente NDJSON ausente o inválida
4  error PostgreSQL
5  error Elasticsearch
10 error interno no clasificado
```

La adaptación del worker para emitir el resultado JSON y la invocación efectiva desde n8n pertenecen a la Fase 10.

## Credenciales

Se utilizan credenciales nativas de n8n:

```text
oscorp-postgres
type: postgres
name: OSCORP Postgres

oscorp-elasticsearch
type: elasticsearchApi
name: OSCORP Elasticsearch
```

Los secretos se obtienen desde `.env`, se importan temporalmente con la CLI y se almacenan cifrados por n8n. El archivo temporal se elimina después de la importación.

`N8N_ENCRYPTION_KEY` se genera localmente cuando falta y nunca se versiona.

## Límites

- El workflow no parseará NDJSON ni construirá SQL.
- n8n no recibirá contraseñas de base de datos dentro del workflow JSON.
- El worker no aceptará rutas de archivos arbitrarias desde el workflow.
- El workflow de Fase 9 es manual, inactivo y solamente verifica conectividad de lectura.
- La programación, reintentos y ejecución productiva quedan para las Fases 10 a 12.

## Consecuencias

- Existe una única implementación de normalización e ingesta.
- El workflow exportado no contiene secretos.
- La integración puede probarse por capas.
- n8n conserva su función de orquestación SOAR-lite.
