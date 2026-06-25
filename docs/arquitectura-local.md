# Arquitectura local LAB

```text
attacker-sim -> cowrie -> cowrie/logs/cowrie.json
                         -> pipeline container
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

pipeline
  Procesador Python contenerizado. No requiere Python instalado en el host.

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
