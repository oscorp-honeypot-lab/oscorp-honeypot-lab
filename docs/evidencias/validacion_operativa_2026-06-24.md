# Validación operativa - 24 de junio de 2026

## Objetivo

Revalidar el estado del perfil LAB después de iniciar Docker Desktop y establecer una nueva evidencia operativa para el roadmap.

## Servicios verificados

```text
oscorp_cowrie
oscorp_attacker_sim
oscorp_postgres
oscorp_elasticsearch
oscorp_kibana
oscorp_n8n
```

Resultados:

```text
PostgreSQL:    acepta conexiones
Elasticsearch: operativo, yellow esperado para nodo único
Kibana:        available
n8n:           2.15.0
```

## Campaña ejecutada

```powershell
docker compose --profile lab run --rm attacker-sim ./run_scenario.sh full
```

La campaña generó 106 eventos entre:

```text
2026-06-24T19:51:20.739091Z
2026-06-24T19:51:40.663607Z
```

Eventos generados:

```text
15 cowrie.session.connect
15 cowrie.session.closed
14 cowrie.command.input
14 cowrie.client.kex
14 cowrie.client.version
10 cowrie.login.success
9  cowrie.log.closed
9  cowrie.session.params
2  cowrie.session.file_download
2  cowrie.login.failed
1  cowrie.command.failed
1  cowrie.client.size
```

## Pipeline ejecutado

```powershell
.\scripts\run_pipeline.ps1
```

Resultado:

```text
events_read=106
events_inserted=106
elasticsearch_indexed=106
status=completed
```

## Estado acumulado

```text
PostgreSQL:
- eventos: 472
- event_hash únicos: 472
- sesiones: 63

Elasticsearch:
- documentos en cowrie-events: 472
```

## Conclusión

El flujo actualmente validado funciona:

```text
attacker-sim -> Cowrie -> cowrie.json
             -> procesador Python
             -> PostgreSQL
             -> Elasticsearch
```

El workflow n8n continúa importado e inactivo. Su ejecución punta a punta permanece pendiente para la fase correspondiente.
