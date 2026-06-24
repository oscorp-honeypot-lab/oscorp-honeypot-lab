# Fase 6 - Validacion de attacker-sim

## Objetivo

Validar que el contenedor `attacker-sim` puede generar ataques reproducibles contra Cowrie dentro del perfil LAB.

## Comando ejecutado

```powershell
docker compose --profile lab run --rm attacker-sim ./run_scenario.sh full
```

## Resultado observado

Antes de la ejecucion final, `cowrie/logs/cowrie.json` tenia 259 eventos.

Despues de la ejecucion final, `cowrie/logs/cowrie.json` tenia 366 eventos.

La corrida genero 107 eventos nuevos entre:

```text
2026-06-11T13:38:23.423648Z
2026-06-11T13:38:42.581033Z
```

## Eventos nuevos relevantes

```text
2  cowrie.login.failed
11 cowrie.login.success
14 cowrie.command.input
2  cowrie.session.file_download
15 cowrie.session.connect
15 cowrie.session.closed
```

## Escenarios validados

```text
[x] brute-force
[x] recon
[x] malware-download
[x] full
```

## Nota tecnica

Cowrie 3.0.0 registro `cowrie.session.file_download` cuando el escenario uso una URL resoluble publicamente (`http://example.com`). Los intentos con IP privada Docker y alias `attacker-sim` quedaron registrados como `cowrie.command.input`, pero no generaron `cowrie.session.file_download` porque el entorno emulado de Cowrie no resolvio esos destinos.

El script `malware_download.sh` conserva la opcion `SERVE_LOCAL_PAYLOAD=true` para pruebas locales, pero la validacion de eventos `file_download` quedo confirmada con la URL documentada por defecto.

## Evidencia generada

```text
docs/evidencias/cowrie_lab_fase6.json
```
