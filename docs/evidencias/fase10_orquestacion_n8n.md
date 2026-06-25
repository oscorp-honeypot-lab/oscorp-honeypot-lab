# Fase 10 - Orquestación efectiva desde n8n

Fecha: 25 de junio de 2026.

## Skills

Se buscaron Skills para:

```text
python internal worker service http api
n8n http request workflow error handling
```

No se instaló ningún Skill de worker privado porque los resultados tenían adopción insuficiente.

Se instaló y utilizó:

```text
n8n-error-handling
Fuente oficial: n8n-io/skills
Evaluación automática: Safe, 0 alerts
```

También se reutilizaron:

```text
n8n-workflow
n8n-credentials-and-security
architecture-patterns
```

## Arquitectura implementada

```text
Manual Trigger n8n
  -> Build Run Request
  -> HTTP POST http://pipeline-worker:8080/runs
  -> Validate Worker Result
  -> Confirm Pipeline Run en PostgreSQL
  -> Validate Pipeline Run
```

`pipeline-worker`:

- utiliza la imagen `oscorp/pipeline:phase10`;
- se ejecuta como usuario no-root;
- no publica puertos al host;
- solo está disponible en `oscorp_net`;
- monta `cowrie/logs` como solo lectura;
- rechaza contratos inválidos;
- impide dos ejecuciones simultáneas mediante un lock;
- devuelve errores funcionales como resultados del contrato y reserva HTTP 500
  para fallos internos no controlados;
- reutiliza `execute_pipeline()` del procesador Python.

No se montó el socket Docker dentro de n8n.

## Workflow

El workflow exportado:

```text
id: oscorp-cowrie-ndjson-pipeline
name: OSCORP - Cowrie Pipeline Orchestration
estado versionado: inactivo
```

El nodo HTTP tiene:

```text
timeout: 120000 ms
retryOnFail: true
maxTries: 3
waitBetweenTries: 2000 ms
```

El resultado del worker se valida contra los campos obligatorios del contrato `1.0`. Después, n8n consulta `pipeline_runs` mediante una consulta parametrizada.

## Compatibilidad

El procesamiento manual continúa disponible:

```powershell
.\scripts\run_pipeline.ps1
```

La ejecución normal desde n8n se realiza con:

```powershell
.\scripts\run_n8n_pipeline.ps1
```

Ambas rutas utilizan la misma función `execute_pipeline()`.

## Validación operativa

Ejecución directa final del workflow:

```text
run_id: 55
status: completed
events_read: 318
events_inserted: 0
events_indexed: 318
errors_count: 0
lastNodeExecuted: Validate Pipeline Run
```

Smoke test con un ataque nuevo:

```text
Primera ejecución n8n:
- run_id: 57
- events_read: 422
- events_inserted: 104
- events_indexed: 422
- errors_count: 0

Segunda ejecución n8n:
- run_id: 58
- events_read: 422
- events_inserted: 0
- events_indexed: 422
- errors_count: 0

Resultado:
- flujo completo validado;
- 104 eventos nuevos;
- 1496 eventos acumulados;
- PostgreSQL y Elasticsearch sincronizados.
```

También se verificó que `run_pipeline.ps1` siguiera completando una ejecución de recuperación sin duplicar eventos.

Estado acumulado final:

```text
PostgreSQL:
- 1496 eventos
- 1496 event_hash únicos
- 260 sesiones
- 26 ejecuciones en pipeline_runs
- último run_id: 58
- último evento: 2026-06-25 07:05:39.936686

Elasticsearch:
- 1496 documentos en cowrie-events

Servicios:
- ocho servicios persistentes en ejecución
- pipeline-worker saludable
- pipeline-worker ejecutado como usuario oscorp
- pipeline-worker sin puertos publicados al host
- n8n 2.15.0
```

Controles adicionales:

```text
- módulos Python compilados dentro de la imagen final
- contrato inválido rechazado con HTTP 400
- validate_lab.ps1 superado
- validate_n8n_contract.ps1 superado
- smoke_test.ps1 -NoBuild superado
```

## Reproducibilidad desde clon limpio

El commit candidato se clonó en una ruta temporal sin `.env`, logs ni
volúmenes previos.

La primera validación detectó que una ejecución con Cowrie todavía vacío no
creaba `pipeline_runs`. Después de corregir ese caso, se descartaron el clon y
sus volúmenes y se repitió toda la prueba desde cero.

Resultado final del segundo clon:

```text
- setup.ps1 superado
- credenciales locales generadas e importadas
- migraciones aplicadas sobre PostgreSQL vacío
- workflow ejecutado con 0 eventos y pipeline_run confirmado
- validate_n8n_contract.ps1 superado
- ataque completo simulado
- primera ingesta: 105 eventos insertados
- segunda ingesta: 0 eventos duplicados
- PostgreSQL: 105 eventos y 105 hashes únicos
- Elasticsearch: 105 documentos
- sesiones: 15
- pipeline_runs: 3
- smoke_test.ps1 -NoBuild superado
```

## Incidencias corregidas

1. El Task Runner de n8n 2.15.0 bloquea `require("crypto")` en Code nodes.
   El UUID de correlación se genera dentro del sandbox sin importar módulos.

2. PowerShell no indexa `MatchCollection[-1]` como un array convencional.
   La salida compacta convierte explícitamente las coincidencias a un array.

3. El script de demo ya había sido ajustado para esperar la escritura asíncrona de Cowrie antes de evaluar el crecimiento del log.

4. Una instalación limpia podía ejecutar el workflow antes de que Cowrie
   generara eventos. El worker ahora crea y finaliza un `pipeline_run` con
   métricas en cero, de modo que n8n siempre puede auditar y confirmar una
   solicitud válida.

## Alcance pendiente

La Fase 10 todavía procesa el NDJSON completo en cada ejecución y se apoya en `event_hash` para evitar duplicados.

El cursor/checkpoint, la rotación del archivo y el procesamiento exclusivamente incremental pertenecen a la Fase 11.
