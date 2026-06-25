# Fase 13.1 - Diseño del modelo de sesiones

Fecha: 25 de junio de 2026.

## Alcance

Se diseñó la entidad analítica de sesión sin implementar todavía migración,
backfill ni cambios en el pipeline.

## Skills

```text
- architecture-patterns
- python-expert-best-practices-code-review
```

También se buscaron Skills para correlación de sesiones y modelos de riesgo.
No se instaló una nueva porque esta subfase requería diseño de dominio y no
una integración adicional.

## Validación contra datos reales

```text
sesiones distintas: 292
complete: 290
open: 0
incomplete: 2
sesiones con múltiples IP por identidad: 0
```

Se confirmó que existen sesiones incompletas y que el modelo no puede asumir
siempre la presencia de `cowrie.session.connect` y `cowrie.session.closed`.

## Resultado

El ADR `docs/decisiones/ADR-0002-modelo-sesiones.md` define:

```text
- identidad session_key por sensor y session_id
- tabla materializada sessions
- estados complete, open e incomplete
- timestamps y duración
- contadores de actividad
- invariantes
- índices previstos
- límites entre resumen y detalle de eventos
```

No se modificó el esquema de base de datos en esta subfase.

Los tres documentos de la entrega se verificaron desde un clon limpio del
commit candidato.
