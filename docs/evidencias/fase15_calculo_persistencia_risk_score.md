# Fase 15 - Cálculo y persistencia del Attack Risk Score

Fecha: 25 de junio de 2026.

## Skills

```text
buscados:
- sqlalchemy alembic postgres audit scoring recalculation python unittest

utilizados:
- sqlalchemy-alembic-expert-best-practices-code-review
- python-expert-best-practices-code-review

instalados: ninguno
descartados: Skills externos redundantes con los ya revisados
```

## Implementación

```text
- evaluador puro por sesión
- migración 0005_session_risk_scores
- persistencia por session_key y rules_version
- razones auditables en JSONB
- recálculo total bajo demanda
- actualización incremental después de correlacionar eventos
- validación integrada al setup, validate_lab y smoke test
```

## Resultado operativo

```text
rules_version: 1.0.0
sesiones después del smoke: 323
scores persistidos: 323
registros inválidos: 0
low: 177
medium: 145
high: 1
critical: 0
pruebas Python: 20/20
recálculo completo: 308 sesiones
Alembic: 0005_session_risk_scores
smoke incremental: 106 eventos y 15 sesiones nuevas
segunda ingesta: 0 eventos nuevos
base vacía: 0 sesiones / 0 scores válido
```

El score más alto observado fue 60 y conserva cinco razones: login exitoso,
usuario privilegiado, reconocimiento, herramienta de descarga y archivo
descargado.

Las reglas reservadas no aportan puntos. Una nueva versión del ruleset crea
una nueva fila por sesión y conserva los resultados de versiones anteriores.

## Clon limpio

```text
base inicial: 0 sesiones / 0 scores válida
instalación y migración 0005: superadas
pruebas Python: 20/20
smoke: 105 eventos
sesiones / scores: 15 / 15
distribución: 6 low, 9 medium, 0 high, 0 critical
segunda ingesta: 0 eventos nuevos
recálculo final: 15 sesiones
```
