# ADR-0003 - Reglas versionadas de Attack Risk Score

Estado: aceptado.

Fecha: 25 de junio de 2026.

## Contexto

OSCORP ThreatLab necesita ordenar sesiones SSH por criticidad sin depender de
Kibana, Telegram ni servicios externos. El resultado debe ser reproducible,
auditable y recalculable cuando cambie el modelo.

## Decisión

Las reglas viven en un módulo de dominio puro, sin acceso a PostgreSQL,
Elasticsearch ni APIs. El conjunto activo se identifica mediante versión
semántica y cada regla tiene identificador estable, peso, señal y descripción.

```text
ruleset: 1.0.0
score mínimo: 0
score máximo: 100
aplicación de cada regla: una vez por sesión
```

## Reglas activas

```text
login_success          +10
privileged_username     +5
reconnaissance         +10
download_tool          +15
file_download          +20
persistence_attempt    +25
```

La suma activa máxima es 85, por lo que una sesión puede alcanzar nivel
crítico aun sin enriquecimientos externos.

## Reglas reservadas

```text
malicious_hash_reputation  +20  deshabilitada
cloud_origin               +10  deshabilitada
```

Estas reglas quedan definidas pero no aportan puntos hasta que existan datos
confiables de VirusTotal y clasificación de origen de red.

## Niveles

```text
0-20:   low
21-50:  medium
51-80:  high
81-100: critical
```

## Consecuencias

- La interfaz futura solo consume resultados y no contiene reglas.
- Cambiar pesos o patrones exige una nueva versión.
- La versión utilizada debe persistirse junto con el score.
- Las razones aplicadas deben conservar los identificadores de regla.
- Fase 15 implementará evaluación, persistencia y recálculo.
