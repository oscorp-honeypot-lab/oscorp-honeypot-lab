# Arquitectura local LAB

```text
attacker-sim -> cowrie -> cowrie/logs/cowrie.json
                         -> n8n
                         -> pipeline-worker
                         -> PostgreSQL:eventos
                         -> Elasticsearch:cowrie-events
                         -> Kibana
```

## Componentes

```text
attacker-sim
  Genera escenarios reproducibles con hydra, sshpass, wget y curl.

cowrie
  Honeypot SSH local publicado en localhost:2222.

n8n
  Orquestador SOAR-lite. Usa credenciales cifradas y un workflow versionado.
  El contrato con el worker esta definido en pipeline/contracts/.

pipeline-worker
  Servicio HTTP privado, no publicado al host. Recibe solicitudes versionadas
  desde n8n, reutiliza el mismo caso de uso del procesador manual y mantiene
  el checkpoint incremental en PostgreSQL.

pipeline_checkpoints
  Conserva offset, línea, fingerprint y última ejecución confirmada. Permite
  continuar después de reinicios y detectar truncado o reemplazo del log.

pipeline
  Entrada de recuperación manual al procesador Python contenerizado. Relee el
  archivo completo sin modificar el checkpoint incremental.

migrate
  Ejecuta migraciones Alembic antes de iniciar consumidores de PostgreSQL.

payload-server
  Sirve payloads inocuos dentro de la red LAB para descargas completamente locales.

PostgreSQL
  Persistencia estructurada de eventos, ejecuciones del pipeline y alertas.

Elasticsearch
  Indexacion de eventos para busqueda y visualizacion.

Kibana
  Capa de exploracion visual.
```

## Identidad de eventos

Cowrie puede repetir `uuid` entre varios eventos. Por eso el pipeline usa `event_hash`, calculado con SHA-256 sobre cada linea NDJSON, como clave unica idempotente.
