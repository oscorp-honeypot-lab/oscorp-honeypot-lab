# Fase 5 — Validación de Cowrie local

## Objetivo

Validar que el sensor Cowrie ejecutado en modo LAB mediante Docker genera eventos en formato NDJSON dentro del archivo `cowrie/logs/cowrie.json`.

## Entorno

- Sistema operativo anfitrión: Windows
- Contenedores activos:
  - oscorp_cowrie
  - oscorp_n8n
  - oscorp_postgres
  - oscorp_elasticsearch
  - oscorp_kibana
  - oscorp_attacker_sim

## Ruta del log en Windows

```text
./cowrie/logs/cowrie.json


Guardá.

---

# 5.10. Estado esperado al terminar la Fase 5

Al final deberías tener:

```text
[x] cowrie/logs/cowrie.json existe
[x] n8n puede leer /files/cowrie/cowrie.json
[x] El log contiene eventos de conexión
[x] El log contiene eventos de login
[x] El log contiene eventos de comandos
[x] Idealmente contiene eventos de descarga
[x] El archivo NDJSON es válido
[x] Se guardó evidencia en docs/evidencias/