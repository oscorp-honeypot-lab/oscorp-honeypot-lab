# Fase 14 - Reglas versionadas de Attack Risk Score

Fecha: 25 de junio de 2026.

## Skills

```text
buscados:
- python risk scoring rules engine dataclasses testing

utilizados:
- architecture-patterns
- python-expert-best-practices-code-review

instalados: ninguno
descartados: scoring comercial, legal y CVE por no corresponder a sesiones Cowrie
```

## Resultado

```text
ruleset: 1.0.0
reglas activas: 6
reglas reservadas: 2
score cap: 100
máximo activo: 85
niveles: low, medium, high, critical
```

Las reglas son inmutables, independientes de infraestructura y verifican
identificadores únicos, pesos positivos, versión semántica y límites.

Las pruebas del dominio se ejecutan como parte de `validate_lab.ps1`.

```text
pruebas Python totales: 13
pruebas superadas: 13
servicios LAB: válidos
sesiones existentes: 308 sin inconsistencias
```

## Clon limpio

```text
instalación desde cero: superada
pruebas Python: 13/13
smoke test: superado
eventos PostgreSQL / Elasticsearch: 106 / 106
sesiones correlacionadas: 15
segunda ingesta: 0 eventos nuevos
```
