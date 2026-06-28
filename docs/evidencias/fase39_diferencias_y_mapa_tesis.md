# Fase 39 - Diferencias con la tesis vieja y mapa de actualizacion

Fecha: 2026-06-27

## Alcance

Este documento cumple dos objetivos de Fase 39:

- registrar las diferencias entre el sistema original de la tesis y OSCORP ThreatLab;
- dejar un mapa de cambios para actualizar mas adelante el PDF de la tesis sin
  inventar resultados ni duplicar explicaciones.

No se crea video demo en esta fase. Tampoco se modifica el PDF final de tesis:
el archivo viejo se conserva como referencia historica.

## Fuente revisada

Archivo analizado:

```text
Tesis_OSCORP_Honeypots_v7(version-4-5-26)_viejo.pdf
```

Extraccion tecnica:

- 75 paginas.
- Indice con 7 capitulos y anexos A-K.
- Desarrollo organizado en 9 fases originales.
- Arquitectura centrada en Cowrie, Docker, n8n, PostgreSQL,
  Elasticsearch, Kibana, VirusTotal, ip-api y Telegram.
- Resultados antiguos basados en experimento controlado de 40 sesiones y
  exposicion inicial a VPS.

## Diferencias principales

| Tema | Tesis vieja | OSCORP ThreatLab actual |
|---|---|---|
| Enfoque operativo | Pipeline SOAR-lite con fuerte dependencia del flujo n8n y una VPS para validacion real. | Dos modos separados: LAB local reproducible y REAL opcional con VPS como sensor externo. |
| Reproducibilidad | Se argumenta reproducibilidad potencial por Docker y herramientas open source. | Reproducibilidad operacional: `setup.ps1`, `validate_lab.ps1`, `smoke_test.ps1`, CI, backup/restore y auditoria de seguridad. |
| Simulacion de ataques | Experimento con Hydra desde VM Ubuntu y sesiones controladas. | `attacker-sim` contenerizado, escenarios versionados, payloads inocuos internos y consola LAB desde la app. |
| Orquestacion | n8n contiene parte importante de parsing/logica. | n8n orquesta; el parsing y la logica autoritativa viven en `pipeline-worker` Python. |
| Persistencia | PostgreSQL para eventos y Elasticsearch/Kibana para analitica. | PostgreSQL como fuente de verdad amplia: eventos, sesiones, usuarios, auditoria, alertas, exportaciones, reportes, checkpoints y modo de origen. |
| Trazabilidad | Basada en eventos, sesiones Cowrie y workflow. | `pipeline_runs`, `pipeline_checkpoints`, `pipeline_event_errors`, `event_hash`, `request_id`, auditoria de usuarios y estados de alertas. |
| Separacion LAB/REAL | VPS aparece como parte central de validacion real. | `source_mode` distingue LAB y REAL en eventos, sesiones, API y UI. La VPS no es requisito para defender el sistema. |
| Visualizacion | Kibana es la interfaz principal de analisis. | App web React/FastAPI es interfaz principal; Kibana queda como apoyo analitico. |
| Seguridad de app | No habia capa propia de identidad web completa. | Login, roles, cookies, CSRF, auditoria, rate limiting de login y rutas protegidas. |
| Riesgo | No existia un modelo persistente amplio de Attack Risk Score. | Reglas versionadas, score por sesion, persistencia, filtros y enriquecimientos por geo/VT. |
| Alertas | Telegram como salida de eventos relevantes. | Modelo de alertas persistente, criterios versionados, dispatcher, reintentos, MTTD y estados. |
| Reportes | No era eje central. | Motor de reportes periodicos, formatos HTML/CSV, entrega/descarga y evidencias. |
| Calidad continua | Validacion funcional manual/documentada. | CI con compose, ruff, type-check, vitest, unit tests, integration tests y cobertura minima. |
| Seguridad operativa | Riesgos de VPS y secretos tratados de forma general. | `.env.example` sin secretos reales, rutas sensibles ignoradas, imagenes externas con digest, retencion/apagado y recomendacion de SSH por clave. |

## Mapa de actualizacion del PDF

### Portada, resumen y abstract

Actualizar:

- nombre del sistema a OSCORP ThreatLab si se decide usarlo como denominacion final;
- mencionar los dos modos: LAB reproducible y REAL opcional;
- sustituir la idea de Kibana como interfaz principal por app web propia + Kibana complementario;
- reemplazar resultados antiguos por resultados finales verificados al momento de cerrar la tesis.

Acotar:

- reducir parrafos largos sobre herramientas individuales;
- mover detalles de configuracion a anexos.

### Capitulo 1 - Introduccion

Conservar:

- problema de logs aislados;
- valor pedagogico de honeypots;
- foco en herramientas open source.

Actualizar:

- problema ampliado: no solo procesar logs, sino hacer el sistema reproducible
  sin depender de una VPS;
- justificar la separacion LAB/REAL;
- ajustar alcance para explicar que el LAB es defendible sin costos externos.

### Capitulo 2 - Marco teorico

Conservar:

- Cowrie, honeypots, SOAR-lite, CTI, PostgreSQL, Elasticsearch, Kibana y Docker.

Actualizar/agregar:

- backend/API web como capa de producto;
- trazabilidad, sesiones correlacionadas y risk scoring;
- CI/reproducibilidad como criterio tecnico;
- nociones de seguridad web aplicadas: autenticacion, roles, CSRF y auditoria.

Acotar:

- evitar repetir historia extensa de cada herramienta si no aporta al diseno final;
- dejar comparaciones comerciales solo como contexto, no como eje central.

### Capitulo 3 - Metodologia

Actualizar:

- cambiar 9 fases originales por fases reestructuradas o por una metodologia
  incremental agrupada por bloques;
- distinguir validacion LAB, validacion REAL y validacion automatizada;
- declarar que las metricas finales deben salir de evidencias reproducibles,
  no de estimaciones no instrumentadas.

Sugerencia de bloques:

1. Infraestructura LAB reproducible.
2. Pipeline, trazabilidad y sesiones.
3. API/app web y seguridad.
4. Enriquecimiento, alertas, MTTD y reportes.
5. Dashboards complementarios.
6. Modo REAL/VPS.
7. Reproducibilidad, CI, backup/restore y auditoria.

### Capitulo 4 - Desarrollo

Reescribir de forma sustancial:

- arquitectura final LAB/REAL;
- contrato n8n -> pipeline-worker;
- modelo de datos actual;
- app web React/FastAPI;
- `source_mode`;
- consola LAB;
- CI y scripts operativos.

Usar como base:

- `docs/arquitectura-final.md`;
- `docs/arquitectura-local.md`;
- `docs/arquitectura-vps.md`;
- evidencias por fase en `docs/evidencias/`.

### Capitulo 5 - Resultados y analisis

No copiar resultados viejos sin aclaracion.

Actualizar solamente con datos medidos al cierre final. Fuentes posibles:

- `scripts/validate_lab.ps1`;
- `scripts/validate_reproducibility.ps1`;
- reportes generados por la app;
- conteos directos de PostgreSQL/Elasticsearch;
- evidencia REAL ya capturada;
- CI de GitHub del commit final.

Evitar:

- extrapolar resultados;
- presentar capturas parciales como estadistica general;
- mezclar LAB y REAL sin indicar `source_mode`.

### Capitulo 6 - Discusion

Actualizar la contrastacion:

- la hipotesis de reproducibilidad queda mas fuerte por el LAB local;
- la hipotesis de trafico real queda como validacion opcional y separada;
- la app web cambia el posicionamiento del sistema: ya no es solo integracion
  de herramientas, sino una plataforma academica operable.

Incluir limitaciones:

- no es un IDS productivo general;
- depende de APIs externas para enriquecimientos;
- Telegram/VT requieren secretos del usuario;
- el modo REAL depende de una VPS expuesta y de gestion responsable de costos.

### Capitulo 7 - Conclusiones y trabajos futuros

Actualizar:

- concluir sobre el valor de la separacion LAB/REAL;
- destacar reproducibilidad, trazabilidad y defensa academica;
- dejar como trabajos futuros: hardening VPS, despliegue remoto completo,
  nuevas reglas de riesgo, mas honeypots y analitica avanzada.

### Anexos

Reemplazar o agregar:

- arquitectura final LAB/REAL;
- esquema actualizado de tablas principales;
- contrato JSON de request/response del pipeline;
- scripts principales (`setup.ps1`, `setup_real.ps1`, `sync_vps_logs.ps1`,
  `validate_lab.ps1`, `validate_reproducibility.ps1`);
- capturas de app web;
- CI y evidencia de tests;
- dashboards Kibana como complemento.

## Reglas para la reescritura final

- No inventar metricas: cada numero debe venir de una evidencia o comando.
- No duplicar explicaciones: teoria en Capitulo 2, implementacion en Capitulo 4,
  resultados en Capitulo 5.
- Separar siempre LAB y REAL.
- Usar tablas para comparar componentes y fases.
- Mantener parrafos cortos y orientados a decisiones tecnicas.
- Dejar anexos para codigo largo, capturas y configuraciones.

## Estado de Fase 39

- Tarea 1 completada: arquitectura final creada en `docs/arquitectura-final.md`
  y guias actualizadas.
- Tarea 2 pendiente: video demo no abordado en esta iteracion.
- Tarea 3 completada: diferencias registradas en este documento.
- Tarea 4 pendiente: el PDF final aun no fue actualizado; este documento deja
  el mapa para hacerlo sin redundancia ni resultados inventados.
