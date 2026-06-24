# Arquitectura REAL / VPS

El modo REAL queda preparado para una etapa posterior donde Cowrie se ejecuta en una VPS publica y el stack local procesa los logs sincronizados.

```text
VPS publica
  Cowrie -> cowrie.json
            |
            v
Host local
  sync_vps.ps1 -> cowrie/logs/cowrie.json
              -> pipeline local
              -> PostgreSQL
              -> Elasticsearch
              -> Kibana / n8n / alertas
```

## Variables reservadas

```env
VPS_HOST=
VPS_USER=
VPS_COWRIE_LOG_PATH=/home/cowrie/cowrie/var/log/cowrie/cowrie.json
```

## Estado

El modo REAL todavia no esta validado en esta reestructuracion. La prioridad actual es dejar el modo LAB reproducible y trazable antes de exponer Cowrie a internet.
