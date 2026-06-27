# OSCORP ThreatLab — Estado, historial y roadmap de reestructuración

> **DOCUMENTO DE LECTURA OBLIGATORIA**
>
> Este archivo es la fuente de verdad operativa del proyecto. Debe leerse antes de analizar, diseñar o modificar el repositorio, y debe actualizarse después de cada cambio validado.
>
> Contiene:
>
> - el contexto del proyecto original;
> - el motivo de la reestructuración;
> - las decisiones técnicas adoptadas;
> - el historial de fases completadas;
> - el estado real y verificable del sistema;
> - los problemas conocidos;
> - el roadmap pendiente.

## Qué es OSCORP ThreatLab

OSCORP ThreatLab es una plataforma académica para capturar, procesar, correlacionar y visualizar actividad maliciosa dirigida a servicios SSH mediante honeypots.

El sistema busca integrar:

```text
Sensor:            Cowrie
Contenedores:      Docker / Docker Compose
Orquestación:      n8n
Persistencia:      PostgreSQL
Indexación:        Elasticsearch
Visualización:     Kibana y una aplicación web propia
Enriquecimiento:   VirusTotal e ip-api
Alertas:           Telegram
Simulación:        attacker-sim con Hydra y sshpass
```

La intención final no es solamente integrar herramientas de terceros. El proyecto debe evolucionar hacia una plataforma propia capaz de:

- reproducir ataques SSH en un entorno controlado;
- analizar eventos y sesiones;
- calcular criticidad y métricas operativas;
- mostrar estadísticas en un dashboard interactivo propio;
- medir el tiempo real de detección y alerta;
- generar reportes;
- permitir, opcionalmente, capturar tráfico real desde una VPS.

## Relación con la tesis original

El archivo:

```text
Tesis_OSCORP_Honeypots_v7(version-4-5-26)_viejo.pdf
```

representa el estado anterior del proyecto, previo a esta reestructuración.

La tesis describe una arquitectura SOAR-lite compuesta por Cowrie, Docker, n8n, PostgreSQL, Elasticsearch, Kibana, VirusTotal, ip-api y Telegram. También documenta nueve fases incrementales que avanzan desde pruebas locales hasta exposición real en una VPS.

Ese diseño original demostró que la integración era posible, pero dejó una dependencia importante:

```text
n8n, PostgreSQL, Elasticsearch y Kibana se ejecutaban en la PC local.
La VPS acumulaba logs mientras la PC estaba apagada.
El procesamiento continuo dependía de que la PC local volviera a estar activa.
```

Esto debilitaba:

- la continuidad real del sistema;
- la reproducibilidad para evaluadores o terceros;
- la posibilidad de probarlo sin pagar una VPS;
- la portabilidad del proyecto;
- su presentación como producto técnico autónomo.

## Objetivo de la reestructuración

La reestructuración separa el sistema en dos modalidades:

```text
Modo LAB / Local:
- Debe ser el modo principal de evaluación.
- Debe poder ejecutarse sin VPS paga.
- Debe generar ataques reproducibles bajo demanda.
- Debe producir datos completos para probar el pipeline.
- Debe ser gratuito, controlado y documentado.

Modo REAL / VPS:
- Debe ser opcional.
- Cowrie se expone a internet para capturar tráfico real.
- Debe reutilizar el mismo modelo de datos, análisis y visualización.
- No debe ser requisito para demostrar el funcionamiento académico.
```

La diferencia principal respecto del proyecto original será una aplicación web propia con dashboard interactivo, estadísticas, análisis por sesión, riesgo, alertas y reportes. Kibana seguirá siendo una herramienta analítica complementaria, no la única interfaz del sistema.

## Regla sobre el PDF de la tesis

El PDF actual debe conservarse como referencia histórica del sistema anterior.

```text
NO modificar todavía la tesis para reflejar cambios parciales.
```

La tesis se actualizará recién cuando:

- la arquitectura reestructurada esté cerrada;
- las funcionalidades principales estén implementadas;
- las pruebas LAB y REAL estén documentadas;
- las métricas finales hayan sido medidas;
- el dashboard propio esté estable;
- las conclusiones puedan escribirse con resultados definitivos.

Hasta ese momento, este archivo reemplaza al PDF como fuente de verdad sobre el estado actual de implementación.

## Reglas de mantenimiento de este roadmap

1. Leer este archivo antes de comenzar cualquier tarea.
2. No marcar una tarea como completada solo porque existe código: debe existir verificación.
3. Guardar evidencia técnica relevante en `docs/evidencias/`.
4. Registrar errores, limitaciones y decisiones, no solamente resultados exitosos.
5. Diferenciar siempre entre:

```text
Implementado
Validado anteriormente
Validado en la sesión actual
Pendiente
Bloqueado
```

6. No modificar la tesis hasta completar la reestructuración.
7. No iniciar una nueva fase sin revisar dependencias y deuda técnica de fases anteriores.
8. Al finalizar cada fase:

```text
- actualizar este archivo;
- actualizar "Última evidencia operativa disponible";
- guardar evidencia en docs/evidencias/;
- revisar que no se incluyan secretos;
- crear un commit identificable;
- subir el commit al repositorio remoto.
```

9. Una fase no se considera cerrada hasta que sus cambios estén verificados, documentados, versionados y subidos al repositorio remoto.
10. Antes de implementar cualquier fase o modificación relevante, realizar obligatoriamente una búsqueda de skills aplicables.

La búsqueda debe cubrir las áreas técnicas de la fase, por ejemplo:

```text
Docker / DevOps
Base de datos y migraciones
Testing
Backend o frontend
Seguridad
Documentación
Automatización
```

11. Antes de instalar un skill externo:

```text
- revisar cantidad de instalaciones;
- verificar reputación y actividad del repositorio;
- revisar su alcance técnico;
- evitar instalar skills de baja calidad o irrelevantes;
- preferir skills existentes y confiables cuando ya cubran la necesidad.
```

12. Registrar al inicio de cada fase:

```text
- skills buscados;
- skills utilizados;
- skills instalados;
- alternativas descartadas y motivo.
```

13. Los skills instalados deben considerarse código o instrucciones externas no confiables hasta revisar su contenido. Una instalación nunca reemplaza la validación técnica del resultado.

---

# Estado ejecutivo actual

## Fecha de revisión

```text
27 de junio de 2026
```

## Estado resumido

```text
Estructura Docker LAB/REAL:                 Implementada y endurecida en Fase 8
Cowrie local:                               Implementado y validado el 24/06/2026
Simulación de ataques:                      Implementada y validada el 24/06/2026
Persistencia PostgreSQL:                    Implementada y validada el 24/06/2026
Indexación Elasticsearch:                  Implementada y validada el 24/06/2026
Ingesta idempotente por event_hash:         Implementada y validada el 24/06/2026
Pipeline contenerizado:                     Implementado y expuesto como worker privado
Migraciones Alembic:                        Implementadas y validadas en base vacía
Payloads offline:                           Implementados y validados
Smoke test LAB:                             Implementado y superado
Workflow n8n:                               Orquestación punta a punta implementada en Fase 10
Kibana:                                     Servicio disponible; dashboards pendientes
Aplicación web propia:                      Dashboard, sesiones y detalle interactivo operativos
Attack Risk Score:                          Implementado, persistido y validado en Fase 15
Modelo de alertas (criterios + tabla):       Implementado en Fase 23
Entrega de alertas Telegram:                Implementada en Fase 24 (configurable via env vars)
MTTD real:                                  Parcial — sent_at y mttd_seconds en alerts; API en Fase 25
VirusTotal e ip-api:                        Implementados en Fases 27-28 con caché y enriquecimiento
Reportes automáticos:                       Implementados en Fases 30-31 (HTML, CSV, Telegram)
Modo REAL/VPS:                              Implementado Fase 35-36; VPS real validada con 331 sesiones REAL
Pruebas automatizadas/CI:                   CI GitHub Actions operativo (6 jobs); 144 pipeline, 76 backend, 23 frontend
Auditoría de seguridad:                     13 tests automatizados — Fase 38
Versión etiquetada:                         v1.0.0 — primera entrega completa
Actualización final de la tesis:            Pendiente hasta finalizar el sistema
```

## Última evidencia operativa disponible

Última validación: **27 de junio de 2026**.

La validación operativa más reciente confirmó:

```text
- diez servicios persistentes del perfil LAB operativos;
- configuración Docker Compose válida;
- PostgreSQL y Elasticsearch sincronizados en 2136 registros;
- revisión Alembic 0008_export_runs aplicada y en head;
- diecisiete scripts PowerShell sin errores de sintaxis;
- parser y migraciones Python válidos dentro del contenedor no-root;
- artefactos y evidencia de instalación desde clon limpio presentes;
- repositorio main sincronizado con origin/main antes de esta fase;
- credenciales n8n de PostgreSQL y Elasticsearch importadas y cifradas;
- workflow manual de contrato ejecutado correctamente desde n8n;
- instalación de Fase 10 validada desde clon limpio y volúmenes vacíos;
- pipeline-worker privado, saludable y accesible solamente desde la red Docker;
- workflow n8n ejecutando, validando y confirmando pipeline_runs;
- smoke test completo utilizando n8n en lugar del pipeline manual;
- ejecución inicial sin eventos registrada correctamente en pipeline_runs;
- clon limpio finalizado con 105 eventos, 15 sesiones y 0 duplicados;
- checkpoint incremental persistente validado después de reiniciar el worker;
- ejecución sucesiva sin novedades con events_read=0;
- recuperación completa sin alterar el checkpoint incremental;
- Fase 11 validada desde clon limpio con 106 eventos y checkpoint en byte 59504;
- trazabilidad por request_id y reintentos idempotentes validados;
- línea inválida aislada sin bloquear la ingesta;
- caída de Elasticsearch recuperada sobre el mismo pipeline_run;
- Fase 12 validada desde clon limpio con fallos controlados;
- modelo de sesiones Fase 13.1 contrastado con 292 sesiones reales:
  290 completas y 2 incompletas;
- proyección final de Fase 13 validada con 308 sesiones:
  306 completas y 2 incompletas.
- Fase 13 reproducida desde clon limpio con 108 eventos, 16 sesiones,
  transición open a complete e idempotencia confirmadas.
- ruleset 1.0.0 de Fase 14 validado con 13 pruebas Python;
- seis reglas activas, dos reservadas y clasificación 0-100 verificada.
- Fase 14 reproducida desde clon limpio con smoke test, 106 eventos,
  15 sesiones y segunda ingesta en cero.
- Fase 15 calculó y persistió 323 scores con versión 1.0.0 y 0 inválidos;
- distribución actual: 177 low, 145 medium, 1 high y 0 critical;
- 20 pruebas Python superadas y recálculo completo verificado.
- smoke incremental de Fase 15: 106 eventos, 15 sesiones nuevas y 0 duplicados.
- Fase 15 reproducida desde clon limpio y base vacía con 20 pruebas,
  105 eventos, 15 scores, recálculo e idempotencia.
- backend FastAPI de Fase 16 saludable como contenedor no-root;
- health live/ready, PostgreSQL async, OpenAPI y logs JSON verificados;
- 3 pruebas backend y 20 pruebas pipeline superadas;
- smoke de Fase 16 finalizado con 2030 eventos y 338 sesiones/scores.
- Fase 16 reproducida desde clon limpio con backend saludable, 3 pruebas,
  smoke de 106 eventos, 15 sesiones/scores e idempotencia.
- identidad Fase 17 validada con Argon2id, sesiones opacas y tres roles;
- CSRF, CORS, rate limit, cabeceras y auditoría verificados;
- 11 pruebas backend y 20 pruebas pipeline superadas;
- smoke de Fase 17 finalizado con 2136 eventos y 353 sesiones/scores.
- Fase 17 reproducida desde clon limpio y base vacía con migración 0006,
  11 pruebas backend, 20 pruebas pipeline, 106 eventos, 15 sesiones/scores,
  un administrador activo e idempotencia confirmada.
- API analítica Fase 18 protegida por rol `viewer`;
- resumen, sesiones, eventos y detalle de sesión disponibles;
- paginación, 404 y exclusión de contraseñas/evento crudo verificadas;
- 15 pruebas backend y 20 pruebas pipeline superadas;
- smoke de Fase 18 finalizado con 2241 eventos, 368 sesiones/scores
  y segunda ingesta en cero.
- Fase 18 reproducida desde clon limpio y base vacía con 15 pruebas backend,
  20 pruebas pipeline, 105 eventos, 15 sesiones/scores, API analítica
  protegida e idempotencia confirmada.
- filtros combinables de Fase 19 verificados para sesiones y eventos;
- revisión operativa protegida para analyst/admin y auditada;
- 17 pruebas backend y 20 pruebas pipeline superadas;
- smoke de Fase 19 finalizado con 2346 eventos, 383 sesiones/scores
  y segunda ingesta en cero.
- exportaciones CSV de sesiones y eventos implementadas en Fase 20;
- límite paginado, UTF-8 con BOM y protección de fórmulas verificados;
- metadatos de éxito y error persistidos en app_export_runs;
- 20 pruebas backend y 20 pruebas pipeline superadas;
- smoke de Fase 20 finalizado con 2451 eventos, 398 sesiones/scores
  y segunda ingesta en cero.
- Fases 19 y 20 reproducidas conjuntamente desde clon limpio y base vacía;
- migración 0008 en head, 20 pruebas backend y 20 pruebas pipeline;
- filtros, revisión, CSV, metadatos, 105 eventos, 15 sesiones/scores
  e idempotencia confirmados.
- frontend React de Fase 21.1 disponible como décimo servicio del LAB;
- rutas, control de sesión y cliente TypeScript generado desde OpenAPI;
- TanStack Query consumiendo resumen y evolución temporal;
- dashboard con métricas, timeline y distribución de riesgo en ECharts;
- build y 2 pruebas frontend, 20 backend y 20 pipeline superados;
- login y dashboard verificados en navegador desktop y móvil sin errores;
- contenedor frontend no-root corregido y validado sin errores de permisos;
- Fase 21 completada con tabla TanStack Table sobre 398 sesiones reales;
- filtros, ordenamiento seguro, 25 filas por página y 16 páginas verificados;
- estados de carga, vacío y error cubiertos por pruebas de componentes;
- responsive desktop/móvil y consola sin errores verificados;
- 5 pruebas frontend, 21 backend y 20 pipeline superadas;
- Fase 22 completada: detalle interactivo de sesión con score, comandos,
  descargas, timeline de eventos y toggle de revisión para analyst/admin;
- patrón container-presentational validado con 7 pruebas de componente;
- navegación desde tabla de sesiones a /sessions/:sessionKey implementada;
- 12 pruebas frontend, 21 backend y 20 pipeline superadas.
- Fase 23 completada: modelo de alertas con migración 0009, motor de criterios
  puro (high_risk/successful_login/file_download), storage con deduplicación,
  integración en pipeline post-scoring y API GET /api/v1/alerts paginada;
- 12 alertas generadas end-to-end desde 15 sesiones existentes;
- constraint UNIQUE(session_key, trigger) verificada (0 duplicados en re-run);
- 9 pruebas pipeline + 5 unit + 4 integration backend superadas;
- 30 pruebas backend y 29 pruebas pipeline superadas.
- Fase 24 completada: entrega de alertas por Telegram con adaptador configurable,
  reintentos controlados (max 3), mttd_seconds calculado al enviar;
- operación silenciosa cuando TELEGRAM_BOT_TOKEN/CHAT_ID no están configurados;
- flujo validado: 12 alertas sent con mock, retry → failed verificado end-to-end;
- 22 pruebas nuevas (15 telegram + 7 dispatcher) → 51 pipeline totales.
- Fase 30 completada: motor de reportes diarios/semanales con migración
  0013_report_runs, dataset JSONB y programación n8n daily/weekly;
- 133 pruebas pipeline en Docker superadas y Alembic aplicado hasta 0013;
- worker validado con triggered_by=n8n_schedule y report_runs daily/weekly
  generados correctamente;
- contrato n8n validado e importación del workflow versionado verificada.
- Fase 31 implementada: reportes HTML/CSV descargables, envío Telegram
  desde API, registro en report_deliveries y panel de entregas en dashboard;
- 57 pruebas backend, 133 pipeline y 12 frontend superadas; build frontend OK.
```

Se verificaron los diez servicios persistentes del perfil LAB en ejecución:

```text
oscorp_cowrie
oscorp_attacker_sim
oscorp_postgres
oscorp_elasticsearch
oscorp_kibana
oscorp_n8n
oscorp_pipeline_worker
oscorp_payload_server
oscorp_backend
oscorp_frontend
```

El servicio transitorio `migrate` completó Alembic correctamente antes de iniciar los consumidores.

Estado de servicios:

```text
PostgreSQL:    acepta conexiones
Elasticsearch: operativo, estado yellow esperado en nodo único
Kibana:        available
n8n:           versión efectiva 2.15.0
Cowrie:        accesible desde attacker-sim en cowrie:2222
Payloads:      accesibles únicamente dentro de la red LAB
Backend:       FastAPI disponible en http://localhost:8000
Frontend:      React disponible en http://localhost:5173
```

Se ejecutó el smoke test completo:

```powershell
.\scripts\smoke_test.ps1 -NoBuild
```

Resultado:

```text
[validate] LAB válido
[demo] Flujo completo validado
[demo] Eventos nuevos en PostgreSQL: 106
[demo] Total acumulado: 1602
[smoke] Prueba integral superada
```

Validación decisiva de reproducibilidad:

```text
Origen: clon local nuevo del commit de Fase 8
Estado inicial: sin .env y con volúmenes Docker vacíos
Comando: .\scripts\smoke_test.ps1

Alembic: 0002_pipeline_checkpoints aplicado correctamente
PostgreSQL: 106 eventos
Elasticsearch: 106 documentos
Segunda ingesta: 0 eventos duplicados
Resultado: prueba integral superada
```

La descarga simulada se realizó sin internet:

```text
http://payload-server:8080/mirai.sh
http://payload-server:8080/bot.sh
```

Resultado del pipeline e idempotencia:

```text
Primera ejecución incremental n8n:
- run_id=64
- events_read=106
- events_inserted=106
- events_indexed=106
- errors_count=0
- source_offset_start=237156
- source_offset_end=296660

Segunda ejecución n8n:
- run_id=65
- events_read=0
- events_inserted=0
- events_indexed=0
- errors_count=0
- source_offset_start=296660
- source_offset_end=296660
```

Estado acumulado de la validación más reciente:

```text
PostgreSQL:
- 2451 eventos
- 2451 event_hash únicos
- 398 sesiones
- 69 ejecuciones en pipeline_runs
- último run_id: 101
- 1 evento inválido en cuarentena

Elasticsearch:
- 2451 documentos en cowrie-events

n8n:
- versión efectiva 2.15.0
- 2 credenciales nativas importadas y cifradas
- workflow OSCORP ejecutado punta a punta

pipeline-worker:
- contrato 1.0
- servicio privado sin puerto publicado
- ejecución concurrente protegida por lock
- checkpoint en byte 772500, línea 1378

Kibana:
- estado general available
```

Evidencia asociada:

```text
docs/evidencias/validacion_operativa_2026-06-24.md
docs/evidencias/fase8_reproducibilidad.md
docs/evidencias/auditoria_fase8_y_replanificacion_2026-06-25.md
docs/evidencias/plan_aplicacion_web_2026-06-25.md
docs/evidencias/fase9_contrato_n8n_pipeline.md
docs/evidencias/fase10_orquestacion_n8n.md
docs/evidencias/fase11_checkpoint_incremental.md
docs/evidencias/fase12_trazabilidad_recuperacion.md
docs/evidencias/fase13_1_diseno_sesiones.md
docs/evidencias/fase13_sesiones_correlacionadas.md
docs/evidencias/fase14_reglas_risk_score.md
docs/evidencias/fase15_calculo_persistencia_risk_score.md
docs/evidencias/fase16_base_api.md
docs/evidencias/fase17_identidad_seguridad.md
docs/evidencias/fase18_api_consulta_analitica.md
docs/evidencias/fase19_filtros_revision.md
docs/evidencias/fase20_exportacion_csv.md
docs/evidencias/fase21_1_base_dashboard.md
docs/evidencias/fase21_cierre_dashboard_sesiones.md
docs/evidencias/fase22_detalle_sesion.md
docs/arquitectura-aplicacion-web-plan.md
```

## Fortalezas actuales

- Separación clara entre perfiles `lab` y `real`.
- Cowrie fijado en una versión conocida.
- Escenarios reproducibles de fuerza bruta, reconocimiento y descarga.
- Evidencias NDJSON conservadas por fase.
- Modelo PostgreSQL corregido para no tratar `event_uuid` como identificador único.
- Uso de `event_hash` para ingesta idempotente.
- Indexación comprobada previamente en Elasticsearch.
- Documentación de arquitectura local, VPS y guía de demo.
- Aplicación React propia con dashboard y exploración operativa de sesiones.

## Riesgos y deuda técnica actuales

### Críticos

- Ninguno identificado en el perfil local reproducible.

### Altos

- PostgreSQL, Elasticsearch, Kibana y n8n publican puertos con configuración de laboratorio y credenciales por defecto.
- El workflow n8n continúa manual e inactivo; la programación periódica todavía está pendiente.
- El modo `real` todavía no aplica endurecimiento, autenticación ni separación de secretos suficiente para exposición pública.
- La imagen `attacker-sim` es grande por las dependencias de Hydra y puede optimizarse en una fase de rendimiento.

### Medios

- No existe CI.
- No hay export de dashboards Kibana.
- No existe todavía el script de sincronización VPS.
- Las evidencias JSON deben revisarse antes de versionar para evitar duplicación o crecimiento innecesario.

---

# Roadmap propuesto — Pendiente de aprobación para implementar

> Las siguientes fases son una propuesta de orden natural. No deben implementarse hasta recibir aprobación explícita.

## Fase 8 — Cerrar la base reproducible

Objetivo: convertir el LAB actual en una instalación realmente repetible para terceros.

- [x] Crear una línea base Git limpia y commits por fase.
- [x] Corregir `.gitignore` para Python, caches y artefactos runtime.
- [x] Eliminar rutas específicas del equipo local.
- [x] Encapsular el procesador dentro de Docker.
- [x] Crear `setup.ps1`, `reset_lab.ps1`, `backup.ps1` y validación automática.
- [x] Agregar healthchecks y dependencias por estado saludable.
- [x] Crear migraciones versionadas para PostgreSQL.
- [x] Lograr el flujo esperado:

```text
git clone
copiar .env.example a .env
docker compose --profile lab up -d
ejecutar demo
```

- [x] Reemplazar la descarga externa de `example.com` por un servidor HTTP interno que Cowrie pueda resolver correctamente.
- [x] Crear un smoke test automatizado del LAB.

### Skills de la fase

```text
Buscados:
- Docker Compose / Docker expert
- Alembic / SQLAlchemy
- PowerShell automation
- smoke test / integration testing
- CI/CD

Instalado:
- docker-expert

Utilizado existente:
- sqlalchemy-alembic-expert-best-practices-code-review

Descartados:
- skills de PowerShell y testing con baja adopción o repositorios de reputación insuficiente.
```

### Resultado

```text
[x] Pipeline sin Python en el host
[x] Alembic validado en base vacía
[x] Healthchecks sin contaminar eventos
[x] Descargas LAB completamente offline
[x] Setup idempotente
[x] Backup validado
[x] Smoke test integral superado
[x] Idempotencia comprobada
[x] Instalación y demo validadas desde clon limpio y volúmenes vacíos
```

## Criterio de descomposición desde la Fase 9

Cada fase futura debe:

```text
- producir un único resultado técnico principal;
- contener preferentemente entre 3 y 5 tareas relacionadas;
- poder validarse y documentarse de forma independiente;
- evitar mezclar dominio, infraestructura, interfaz y despliegue;
- terminar con evidencia, actualización de este archivo, commit y push.
```

Equivalencia con el roadmap anterior:

```text
Fase anterior 9  -> Fases 9 a 12
Fase anterior 10 -> Fases 13 a 15
Fase anterior 11 -> Fases 16 a 22
Fase anterior 12 -> Fases 23 a 25
Fase anterior 13 -> Fases 26 a 29
Fase anterior 14 -> Fases 30 y 31
Fase anterior 15 -> Fases 32 y 33
Fase anterior 16 -> Fases 34 a 36
Fase anterior 17 -> Fases 37 a 39
```

Skills evaluados para esta replanificación:

```text
Buscados:
- software roadmap planning
- task decomposition project planning
- technical documentation / ADR

No instalados:
- los candidatos encontrados tenían adopción baja o moderada y no superaban
  el umbral de confianza definido para incorporar dependencias nuevas.

Utilizado:
- architecture-patterns, para separar dominio, casos de uso, adaptadores
  e infraestructura y ordenar las dependencias entre fases.
- fastapi-templates, para definir estructura, inyección de dependencias,
  validación, acceso asíncrono y pruebas del backend.
```

## Plan técnico previsto para la aplicación web

La aplicación propia se construirá como un monolito modular desplegado con Docker Compose:

```text
Backend:
- Python 3.12
- FastAPI
- Pydantic v2
- SQLAlchemy 2 asíncrono + psycopg 3
- Alembic como única fuente de migraciones
- PostgreSQL como sistema de registro

Frontend:
- React + TypeScript
- Vite
- React Router
- TanStack Query
- TanStack Table
- Apache ECharts
- Leaflet / React Leaflet
- Lucide Icons
- CSS Modules y variables de diseño

Integración:
- API REST versionada en /api/v1
- contrato OpenAPI
- cliente TypeScript generado desde OpenAPI
- servicio web-gateway del mismo origen para frontend y API

Calidad:
- pytest y HTTPX para backend
- Vitest y Testing Library para frontend
- Playwright para recorridos end-to-end
```

Seguridad prevista:

```text
- usuarios y roles viewer, analyst y admin;
- contraseñas con Argon2id;
- sesiones almacenadas del lado servidor;
- cookies HttpOnly, Secure en producción y SameSite;
- protección CSRF para operaciones de escritura;
- no almacenar JWT ni secretos en localStorage;
- CORS con allowlist explícita;
- validación estricta de entradas, límites de paginación y exportación;
- rate limiting para login, exportaciones y endpoints costosos;
- cabeceras de seguridad y política de contenido;
- registro de auditoría para login, revisión, exportación y administración;
- secretos únicamente mediante variables o archivos no versionados.
```

La estructura, decisiones y límites completos están documentados en:

```text
docs/arquitectura-aplicacion-web-plan.md
```

## Fase 9 — Contrato de integración entre n8n y el pipeline

Objetivo: decidir y documentar cómo n8n ejecutará el procesamiento.

- [x] Definir si Python opera como worker principal o herramienta de recuperación.
- [x] Definir entradas, salidas, códigos de error y límites del procesamiento.
- [x] Configurar credenciales reproducibles de PostgreSQL y Elasticsearch en n8n.
- [x] Exportar la decisión y la configuración sin incluir secretos.

### Skills de la fase

```text
Instalados y utilizados:
- n8n-workflow
- n8n-credentials-and-security

Utilizado existente:
- architecture-patterns
```

### Resultado

```text
[x] ADR-0001 aceptado
[x] n8n definido como orquestador
[x] Python definido como worker autoritativo
[x] contratos request/result versionados
[x] credenciales PostgreSQL y Elasticsearch cifradas
[x] clave n8n estable y no versionada
[x] workflow de comprobación seguro, manual e inactivo
[x] validación automatizada superada
[x] smoke test sin regresiones
[x] clon limpio con clave, credenciales, workflow y 106 eventos validado
```

## Fase 10 — Orquestación efectiva desde n8n

Objetivo: ejecutar el pipeline contenerizado desde el workflow.

- [x] Disparar el procesamiento NDJSON desde n8n.
- [x] Persistir en PostgreSQL e indexar en Elasticsearch sin comandos manuales del host.
- [x] Exportar el workflow actualizado y reproducible.
- [x] Validar una ejecución completa iniciada desde n8n.

### Skills de la fase

```text
Instalado y utilizado:
- n8n-error-handling

Reutilizados:
- n8n-workflow
- n8n-credentials-and-security
- architecture-patterns
```

### Resultado

```text
[x] pipeline-worker privado y no-root
[x] contrato HTTP 1.0 validado
[x] workflow n8n con timeout y reintentos
[x] consulta pipeline_runs parametrizada
[x] demo normal migrada a n8n
[x] recuperación manual conservada
[x] 104 eventos nuevos insertados desde n8n
[x] segunda ejecución con 0 duplicados
[x] 1496 eventos sincronizados
[x] clon limpio validado desde cero con 105 eventos
[x] ejecución sin eventos auditable mediante pipeline_runs
```

## Fase 11 — Checkpoint e idempotencia del workflow

Objetivo: procesar solamente los eventos pendientes.

- [x] Diseñar cursor, offset o checkpoint persistente.
- [x] Evitar reprocesamiento después de reinicios.
- [x] Definir recuperación cuando cambia o se rota `cowrie.json`.
- [x] Probar ejecuciones sucesivas sin duplicados ni pérdida de eventos.

### Skills de la fase

```text
Utilizados:
- n8n-workflow
- python-expert-best-practices-code-review

Búsqueda adicional:
- checkpoint incremental NDJSON
- cursor persistente
- rotación de archivos
```

### Resultado

```text
[x] migración 0002_pipeline_checkpoints
[x] lectura binaria desde byte_offset
[x] líneas parciales conservadas para la siguiente ejecución
[x] detección de truncado y reemplazo
[x] checkpoint actualizado solo después de PostgreSQL y Elasticsearch
[x] reinicio del worker con events_read=0
[x] recuperación completa sin mover el checkpoint
[x] cinco pruebas automáticas superadas
[x] smoke incremental: 106 eventos nuevos y segunda lectura en cero
[x] 1602 eventos sincronizados
[x] clon limpio: 106 eventos, 15 sesiones y checkpoint persistente
```

## Fase 12 — Trazabilidad y recuperación del pipeline

Objetivo: hacer observable y resistente la orquestación.

- [x] Registrar cada ejecución en `pipeline_runs`.
- [x] Manejar eventos inválidos y errores parciales.
- [x] Agregar reintentos controlados y estados finales claros.
- [x] Validar fallos y recuperación punta a punta con evidencia.

### Skills de la fase

```text
- n8n-error-handling
- python-expert-best-practices-code-review
```

### Resultado

```text
[x] migración 0003_pipeline_traceability
[x] request_id único y attempt_count
[x] reintentos idempotentes
[x] cuarentena pipeline_event_errors
[x] estado completed_with_errors
[x] reintentos Elasticsearch limitados a 3
[x] recuperación sobre el mismo run_id
[x] siete pruebas Python superadas
[x] smoke test integral superado
[x] clon limpio con cuarentena y recuperación validado
```

## Fase 13 — Modelo de sesiones correlacionadas

Objetivo: construir la unidad analítica principal del sistema.

- [x] Diseñar la entidad, tabla o vista de sesiones.
- [x] Agrupar eventos por `session_id`.
- [x] Calcular inicio, fin, duración y resumen de actividad.
- [x] Crear la migración y validar sesiones completas e incompletas.

### Subfases

```text
[x] Fase 13.1 - Diseño del modelo de sesión
[x] Fase 13.2 - Agrupación y proyección
[x] Fase 13.3 - Tiempos y resumen de actividad
[x] Fase 13.4 - Migración, backfill y validación
```

### Resultado de Fase 13.1

```text
[x] tabla materializada sessions seleccionada
[x] identidad session_key definida
[x] estados complete, open e incomplete definidos
[x] campos, índices e invariantes documentados
[x] diseño contrastado con 292 sesiones reales
[x] migración 0004 y backfill aplicados
[x] upsert incremental integrado al pipeline
[x] transición open a complete validada
[x] 308 sesiones correlacionadas sin inconsistencias
[x] clon limpio: 108 eventos, 16 sesiones y 0 duplicados
[x] escritura sintética NDJSON corregida a UTF-8 sin BOM
```

## Fase 14 — Reglas versionadas de Attack Risk Score

Objetivo: definir el modelo de puntuación propio sin acoplarlo a la interfaz.

- [x] Definir reglas, pesos, versión y límites del score.
- [x] Incluir login exitoso, usuarios privilegiados, reconocimiento, descarga y persistencia.
- [x] Reservar señales para reputación de hashes y origen cloud.
- [x] Definir niveles Bajo, Medio, Alto y Crítico.

```text
0-20:  Bajo
21-50: Medio
51-80: Alto
81+:   Crítico
```

### Resultado

```text
[x] ruleset 1.0.0 independiente de infraestructura
[x] seis reglas activas con máximo de 85 puntos
[x] dos reglas de enriquecimiento reservadas y deshabilitadas
[x] límites 0, 20, 21, 50, 51, 80, 81 y 100 cubiertos por pruebas
[x] 13 pruebas Python superadas dentro del contenedor no-root
[x] clon limpio con smoke test e idempotencia superados
```

## Fase 15 — Cálculo, persistencia y pruebas del Risk Score

Objetivo: aplicar el score a sesiones reales de forma auditable.

- [x] Calcular el score por sesión.
- [x] Registrar los motivos y la versión de reglas utilizada.
- [x] Permitir recalcular sesiones al cambiar las reglas.
- [x] Crear pruebas unitarias y casos límite.

### Resultado

```text
[x] migración 0005_session_risk_scores aplicada
[x] 323 sesiones con score versionado y razones JSONB
[x] cálculo incremental integrado al pipeline
[x] recálculo completo mediante script reproducible
[x] 20 pruebas Python superadas
[x] distribución validada: 177 low, 145 medium, 1 high, 0 critical
[x] smoke incremental: 106 eventos, 15 sesiones y segunda ingesta en cero
[x] clon limpio: base vacía válida, 105 eventos y 15 scores recalculables
```

## Fase 16 — Base arquitectónica de la API

Objetivo: crear el backend de OSCORP ThreatLab con límites claros.

- [x] Crear el servicio FastAPI con Python 3.12, Pydantic v2 y configuración tipada.
- [x] Aplicar un monolito modular con `domain`, `application`, `adapters`, `infrastructure` y `api`.
- [x] Configurar SQLAlchemy 2 asíncrono, psycopg 3 y una única cadena de migraciones Alembic.
- [x] Contenerizar el backend y exponer healthcheck, logs estructurados y OpenAPI.

### Resultado

```text
[x] backend FastAPI 0.138.1 en Python 3.12.4
[x] health live/ready con dependencia PostgreSQL
[x] OpenAPI y Swagger UI disponibles
[x] logs JSON y x-request-id
[x] contenedor no-root UID 10002
[x] 3 pruebas backend y smoke integral superados
[x] clon limpio con 106 eventos, 15 sesiones/scores y 0 duplicados
```

## Fase 17 — Identidad y seguridad de la aplicación

Objetivo: proteger la aplicación antes de exponer operaciones y datos.

- [x] Crear usuarios, roles `viewer`, `analyst` y `admin`, y registro de auditoría.
- [x] Implementar Argon2id y sesiones de servidor con cookies HttpOnly, SameSite y Secure en producción.
- [x] Implementar CSRF, CORS por allowlist, rate limiting y cabeceras de seguridad.
- [x] Proteger endpoints por permisos y probar autenticación, autorización, cierre y expiración de sesión.
- [x] Mantener secretos fuera de Git y evitar tokens de acceso en `localStorage`.

### Resultado

```text
[x] migración 0006_identity_security
[x] administrador local generado sin versionar su contraseña
[x] sesiones opacas persistidas y revocables
[x] roles viewer, analyst y admin verificados
[x] CSRF, CORS, rate limit y cabeceras de seguridad
[x] auditoría de identidad y administración
[x] 11 pruebas backend y smoke integral superados
[x] clon limpio con 106 eventos, 15 sesiones/scores, un administrador y 0 duplicados
```

## Fase 18 — API de consulta analítica

Objetivo: exponer los datos principales para el dashboard.

- [x] Crear endpoint de resumen general.
- [x] Crear listado paginado de sesiones y eventos.
- [x] Crear detalle de sesión con comandos, descargas y score.
- [x] Agregar pruebas de integración de lectura.

### Resultado

```text
[x] resumen general contrastado contra PostgreSQL
[x] sesiones y eventos paginados con límite máximo de 100
[x] detalle con comandos, descargas, score y línea temporal
[x] endpoints protegidos por rol viewer
[x] password y raw_event excluidos de las respuestas
[x] 15 pruebas backend, 20 pruebas pipeline y smoke integral superados
[x] clon limpio con 105 eventos, 15 sesiones/scores y 0 duplicados
```

## Fase 19 — API de filtros y revisión operativa

Objetivo: soportar el trabajo de análisis sobre las sesiones.

- [x] Filtrar por tiempo, IP, país, usuario, evento y criticidad.
- [x] Permitir marcar y desmarcar sesiones como revisadas.
- [x] Registrar fecha y estado de revisión.
- [x] Probar filtros combinados y transiciones de estado.

### Resultado

```text
[x] migración 0007_session_review
[x] filtros combinables con parámetros SQL enlazados
[x] país preparado para datos enriquecidos
[x] revisión protegida por rol analyst y CSRF
[x] actor, fecha y auditoría de transiciones
[x] 17 pruebas backend, 20 pruebas pipeline y smoke integral
[x] clon limpio conjunto con Fase 20: filtros y revisión verificados
```

## Fase 20 — API de exportación

Objetivo: permitir extraer datos sin depender de Kibana.

- [x] Exportar sesiones y eventos filtrados a CSV.
- [x] Definir límites y paginación para exportaciones grandes.
- [x] Registrar errores y metadatos de la exportación.
- [x] Agregar pruebas de contenido y codificación.

### Resultado

```text
[x] migración 0008_export_runs
[x] CSV filtrado de sesiones y eventos
[x] máximo 1000 filas por página y totales en cabeceras
[x] UTF-8 con BOM, CRLF y neutralización de fórmulas
[x] metadatos persistidos para éxito y error
[x] 20 pruebas backend, 20 pruebas pipeline y smoke integral
[x] clon limpio conjunto: 20 pruebas backend, 105 eventos y 0 duplicados
```

## Fase 21 — Base React y dashboard operativo

Objetivo: crear la primera interfaz propia utilizable.

- [x] Crear React + TypeScript + Vite con rutas, layout operativo y control de sesión.
- [x] Generar el cliente TypeScript desde OpenAPI y consumirlo con TanStack Query.
- [x] Crear resumen, evolución temporal y distribución de riesgo con Apache ECharts.
- [x] Crear tabla de sesiones con TanStack Table, filtros, paginación y ordenamiento.
- [x] Definir componentes accesibles, diseño responsive y estados de carga, vacío y error.

### Resultado final

```text
[x] servicio frontend Docker no-root y saludable
[x] login y logout basados en cookies de servidor
[x] cliente TypeScript generado desde OpenAPI
[x] TanStack Query para sesión, resumen y timeline
[x] endpoint horario de 1 a 720 horas
[x] métricas, evolución temporal y distribución de riesgo
[x] validación desktop 1280x720 y móvil 390x844
[x] tabla de 398 sesiones con filtros combinables
[x] paginación de servidor y selector de 25, 50 o 100 filas
[x] ordenamiento seguro de servidor con lista blanca
[x] estados accesibles de carga, vacío, error y actualización
[x] enlace de salto, foco visible, aria-sort y navegación por teclado
[x] validación desktop y móvil sin overflow global
[x] 5 pruebas frontend, 21 backend y 20 pipeline
```

## Fase 22 — Detalle interactivo de sesión

Objetivo: completar el flujo principal de análisis.

- [x] Mostrar timeline, eventos, comandos y descargas.
- [x] Mostrar Risk Score y motivos.
- [x] Alertas: pendiente hasta Fase 23 (tabla de alertas aún no existe).
- [x] Permitir marcar la sesión como revisada.
- [x] Mantener Kibana como herramienta complementaria.

### Skills de la fase

```text
Buscados:
- React Router session detail navigation
- TanStack Query useMutation review
- Vitest Testing Library accessibility

Utilizados existentes:
- tanstack-query, react-router-dom, browser:control-in-app-browser

Instalados:
- ninguno; todas las dependencias ya estaban presentes
```

### Resultado

```text
[x] SessionDetailPage con patrón container-presentacional
[x] SessionDetailView exportado e independientemente testeable
[x] ruta /sessions/:sessionKey en React Router
[x] Link en primera celda de SessionsPage hacia el detalle
[x] getSessionDetail y reviewSession en client.ts
[x] toggle de revisión con CSRF y actualización optimista de cache
[x] botón visible solo para analyst y admin
[x] header: IP, session_id, fechas, duración, usuario, país
[x] score card con número, nivel y lista de reglas activadas
[x] sección de comandos en lista monoespaciada
[x] sección de descargas con URL y SHA-256
[x] timeline de eventos con tipo, timestamp y detalle
[x] estados loading, notFound y error con roles ARIA correctos
[x] responsive desktop y móvil sin overflow
[x] 7 pruebas nuevas → 12 pruebas frontend totales
[x] 21 pruebas backend y 20 pruebas pipeline sin regresiones
```

## Fase 23 — Modelo y políticas de alertas

Objetivo: definir qué genera una alerta y cómo se registra.

```text
[x] Completar la tabla alerts mediante migración 0009_alerts_model.
[x] Incluir session_key FK, event_hash FK, pipeline_run_id FK, timestamps, MTTD, canal, estado y error.
[x] Definir criterios de alerta: high_risk (score high/critical), successful_login, file_download.
[x] Registrar event_timestamp (del evento origen) y triggered_at (procesamiento pipeline).
[x] Definir estados: pending, sent, failed, suppressed; canal: telegram, log, webhook.
[x] Motor de criterios puro en pipeline/alerts/criteria.py (sin DB, testeable unitariamente).
[x] Persistencia con deduplicación UNIQUE(session_key, trigger) en pipeline/alerts/storage.py.
[x] Integración post-scoring en process_cowrie_ndjson.py.
[x] API GET /api/v1/alerts con paginación y filtros (status, sessionKey), rol viewer.
[x] 9 pruebas pipeline + 5 unit backend + 4 integration backend → 30 backend, 29 pipeline.
[x] 12 alertas generadas end-to-end desde 15 sesiones del entorno LAB.
Evidencia: docs/evidencias/fase23_modelo_alertas.md
```

## Fase 24 — Entrega de alertas por Telegram

Objetivo: enviar alertas y registrar su resultado real.

```text
[x] Integrar Telegram mediante TelegramAdapter configurable (urllib.request, sin deps nuevas).
[x] Gestionar token y destino sin versionar secretos: ${TELEGRAM_BOT_TOKEN:-} en docker-compose.yml.
[x] Operación silenciosa cuando las variables no están configuradas (dispatch retorna 0).
[x] Registrar envíos exitosos: status=sent, sent_at, mttd_seconds calculado.
[x] Registrar fallos: attempt_count++, error_code, error_detail; status=failed al agotar intentos.
[x] Reintentos controlados: MAX_ATTEMPTS=3, carga solo pending con attempt_count < max.
[x] Migración 0010_alert_attempt_count agrega attempt_count INTEGER NOT NULL DEFAULT 0.
[x] format_alert_message() con HTML (negritas, code) y emojis de nivel de riesgo.
[x] 22 pruebas nuevas: 15 telegram + 7 dispatcher → 51 pruebas pipeline totales.
[x] Flujo validado con mock adapter: 12 alertas sent, mttd=4209s; retry → failed verificado.
[x] Formato de mensaje rediseñado: encabezado visual, src_ip, username, duration, downloads.
[x] dispatcher.py: LEFT JOIN sessions para obtener los campos extra del atacante.
[x] format_alert_message() acepta src_ip, username, duration_seconds, download_count (opcionales).
[x] Timestamp formateado como dd-mm-yyyy HH:MM:SS UTC; eliminado parse_mode HTML (texto plano).
[x] 10 tests nuevos para el nuevo formato → 61 pruebas pipeline totales.
Evidencia: docs/evidencias/fase24_telegram_alertas.md
```

## Fase 25 — Medición real de MTTD

Objetivo: reemplazar la estimación teórica por métricas evento-alerta.

```text
[x] MttdTriggerStat y MttdStats en domain/analytics.py.
[x] PERCENTILE_CONT(0.95) + AVG + MIN + MAX sobre mttd_seconds en SQL.
[x] failure_rate = total_failed / (total_sent + total_failed).
[x] Breakdown por trigger (GROUP BY trigger, ordered-set aggregate).
[x] GET /api/v1/analytics/mttd → MttdStatsResponse (requiere VIEWER).
[x] Panel MttdPanel en DashboardPage.tsx: 6 métricas + tabla breakdown.
[x] SDK regenerado con openapi-ts desde el container frontend.
[x] 8 tests nuevos (4 unit + 4 integration) → 38 backend totales.
[x] TypeScript sin errores (tsc --noEmit).
Evidencia: docs/evidencias/fase25_mttd_real.md

Resultados reales (LAB):
  MTTD promedio: ~21 min | mínimo: 16s | máximo: ~4h | p95: ~70 min
  46 alertas sent | 1 failed (http_429) | failure_rate: 2.13%
```

## Fase 26 — Enriquecimiento geográfico de IPs

Objetivo: contextualizar el origen de las conexiones.

```text
[x] Migración 0011_ip_geo_cache: tabla con ip PK, country, country_code, city,
    isp, asn, latitude, longitude, queried_at, expires_at, error.
[x] IpApiAdapter: urllib.request + ipaddress stdlib, sin nuevas dependencias.
    Detecta IPs privadas (RFC 1918) sin llamar a la API — error="private_range".
[x] Caché con TTL 7 días (configurable): ON CONFLICT (ip) DO UPDATE.
    LIMIT 30 IPs por run para respetar rate limit de ip-api (45 req/min).
[x] Errores registrados: private_range, api_fail:{msg}, rate_limited, url_error.
[x] Backend SESSION_SELECT: LEFT JOIN ip_geo_cache como fallback de country.
[x] 21 tests nuevos (9 adapter + 7 cache + 5 enricher) → 82 pipeline totales.
[x] Backend: 38/38 sin regresiones.
Evidencia: docs/evidencias/fase26_geo_enriquecimiento.md

LAB: IPs son privadas (172.25.0.x) → error=private_range, country=NULL.
     Con IPs reales: country/city/isp/lat/lon almacenados y expuestos en /sessions.
```

## Fase 27 — Enriquecimiento de hashes con VirusTotal

Objetivo: contextualizar los archivos descargados.

```text
[x] Migración 0012_vt_hash_cache: sha256 PK, malicious, suspicious, undetected,
    harmless, timeout (INTEGER), last_analysis_date BIGINT, reputation INTEGER,
    queried_at, expires_at, error TEXT.
[x] VirusTotalAdapter: GET api/v3/files/{sha256} x-apikey (VT_API_KEY env),
    sin nuevas deps (urllib.request). Sin clave → error="no_api_key" sin llamada HTTP.
    Errores tipados: rate_limited, not_found, http_error:{code}, url_error:{r}.
[x] Caché con TTL 30 días (análisis VT es estable); ON CONFLICT (sha256) DO UPDATE.
    LIMIT 10/run (VT free: 4 req/min). no_api_key no se almacena para permitir reintento.
[x] Backend: VtStats + GET /api/v1/analytics/vt-stats (total_cached, malicious_detected,
    not_found, error_count, max_malicious).
[x] 20 tests pipeline (8+7+5) → 102 total; 6 tests backend (3+3) → 44 total.
Evidencia: docs/evidencias/fase27_virustotal_hashes.md

LAB: no hay eventos cowrie.session.file.download → 0 hashes, tabla vacía.
     Con hashes reales y VT_API_KEY configurada: enriquecimiento automático.
```

## Fase 28 — Enriquecimiento aplicado al Risk Score

Objetivo: incorporar contexto externo sin volver inestable el score.

```text
[x] Ruleset v1.1.0: malicious_hash_reputation (weight=20) y cloud_origin (weight=10)
    habilitadas. Anteriormente reservadas desde Fase 14.
[x] is_cloud_provider(isp, asn): frozenset de 17 keywords (amazon, aws, google,
    microsoft, azure, digitalocean, linode, vultr, ovh, hetzner, cloudflare, fastly,
    akamai, tencent, alibaba, huawei) con match case-insensitive en isp+asn.
[x] SessionRiskInput: vt_malicious_hashes=0 e is_cloud_origin=False como defaults
    seguros (sin enriquecimiento = regla NO dispara — conservador).
[x] LOAD_SESSIONS_SQL: subquery COUNT vt_hash_cache (malicious>0, error NULL,
    no expirado) + LEFT JOIN ip_geo_cache para isp/asn.
[x] Recalculación masiva: 75 sesiones LAB actualizadas a v1.1.0.
[x] Backend: rules_version 1.0.0 → 1.1.0 (main.py ×2 + analytics_repository.py ×1
    + fixture de test de integración ×1).
[x] 17 tests nuevos pipeline → 119 totales; 44 backend sin cambios.
Evidencia: docs/evidencias/fase28_enriquecimiento_risk_score.md

LAB: IPs privadas (private_range) + sin descargas → ambas reglas no disparan.
     Correcto: el score 1.1.0 = score 1.0.0 para datos del LAB.
     Con datos reales: +20pts hashes maliciosos, +10pts origen cloud.
```

## Fase 29 — Visualización geográfica ✅

Objetivo: representar actividad por ubicación.

```text
[x] Definir el mapeo geo_point en Elasticsearch: campo src_location añadido a
    cowrie-events (ensure_index + _update_index_geo_mapping para índices existentes).
[x] Crear el mapa geográfico en Kibana: guía documentada en kibana/geo_map_guide.md.
    El mapping ya permite crear el mapa en Kibana Maps. Configuración visual en Fase 32.
[x] Crear la visualización equivalente en la aplicación propia: GeoPanel en
    DashboardPage con stats (unique_countries, total_with_geo, cobertura, sin_geo)
    + tabla top 20 países con flags Unicode.
[x] Validar sesiones sin coordenadas o con datos incompletos: estado vacío
    descriptivo en GeoPanel, total_without_geo en el endpoint.
[x] 9 tests nuevos pipeline + 6 tests nuevos backend → 128 pipeline, 50 backend.
```

Evidencia: docs/evidencias/fase29_visualizacion_geografica.md

LAB: IPs privadas (172.25.x.x) → private_range → sin geo_point en ES → by_country=[].
     GeoPanel muestra estado vacío explicativo. Correcto para el entorno LAB.

## Fase 30 — Motor de reportes periódicos ✅

Objetivo: generar conjuntos de datos diarios y semanales.

- [x] Calcular eventos, IPs, sesiones, países, credenciales y comandos principales.
- [x] Incluir archivos, hashes maliciosos, sesiones críticas, MTTD y alertas fallidas.
- [x] Programar reportes diarios y semanales.
- [x] Validar resultados contra consultas directas.

Evidencia: docs/evidencias/fase30_motor_reportes_periodicos.md

LAB: reportes idempotentes por periodo en `report_runs`. Validación Docker:
133 pruebas pipeline OK, Alembic en `0013_report_runs`, worker schedule OK
y contrato n8n validado.

## Fase 31 — Formatos y entrega de reportes ✅

Objetivo: distribuir reportes reproducibles.

- [x] Generar HTML o PDF y CSV.
- [x] Permitir descarga desde la aplicación.
- [x] Permitir envío por Telegram.
- [x] Registrar generación, entrega y errores.

Evidencia: docs/evidencias/fase31_formatos_entrega_reportes.md

LAB: HTML + CSV descargables desde API/dashboard; Telegram registra
`skipped` si no hay credenciales y `report_deliveries` audita entregas.

## Fase 32 — Dashboards operativos de Kibana ✅

Objetivo: crear una capa complementaria para operación y tiempo.

- [x] Crear el data view de `cowrie-events`.
- [x] Crear paneles de eventos, sesiones y evolución temporal.
- [x] Crear filtros y tablas operativas.
- [x] Validar los paneles con datos LAB.

Evidencia: docs/evidencias/fase32_dashboards_operativos_kibana.md

LAB: `scripts/configure_kibana_phase32.ps1` crea/reutiliza el data view,
5 visualizaciones, una búsqueda guardada y el dashboard
`oscorp-phase32-operational`. Validado contra 2451 documentos en
`cowrie-events`; verificación visual OK con 6 paneles renderizados.

## Fase 33 — Dashboards analíticos de Kibana versionados ✅

Objetivo: completar y volver importable la capa Kibana.

- [x] Crear visualizaciones de riesgo y mapa geográfico.
- [x] Exportar objetos a `kibana/dashboards.ndjson`.
- [x] Automatizar o documentar la importación.
- [x] Validar exportación e importación desde una instancia limpia.

Evidencia: docs/evidencias/fase33_dashboards_analiticos_kibana.md

LAB: `scripts/configure_kibana_phase33.ps1` crea el índice analítico
`oscorp-session-risk`, sincroniza 398 sesiones con score, crea dashboard
analítico con riesgo + mapa, exporta objetos versionados e importa el NDJSON
en un space limpio temporal para validación.

## Fase 33.5 — Consola LAB de simulaciones desde la app ✅

Objetivo: convertir el LAB en una experiencia operable desde la aplicación web,
sin requerir que el evaluador ejecute ataques y pipeline desde terminal.

Esta fase queda intencionalmente antes de la Fase 34 porque pertenece al modo
LAB/local. No debe mezclar todavía decisiones del modo REAL/VPS.

Flujo esperado:

```text
App web -> Laboratorio -> elegir escenario -> ejecutar
          -> salida tipo terminal en pantalla
          -> attacker-sim genera el ataque
          -> pipeline-worker procesa cowrie.json
          -> dashboard/sesiones/Telegram se actualizan
```

Escenarios permitidos:

```text
brute-force
recon
malware-download
full
```

Restricciones de seguridad:

- [x] No ejecutar comandos arbitrarios enviados desde la web.
- [x] Usar allowlist estricta de escenarios conocidos.
- [x] Habilitar la funcionalidad solamente en `OSCORP_API_ENVIRONMENT=lab`.
- [x] Requerir rol `analyst` o `admin`.
- [x] Permitir una sola ejecución LAB concurrente.
- [x] No montar el Docker socket en el backend.
- [x] No exponer servicios internos del LAB fuera de la red Docker.
- [x] Registrar actor, escenario, timestamps, estado, exit code y resumen.

Diseño técnico implementado:

- [x] Crear tabla `lab_runs` para historial de ejecuciones (`0015_lab_runs`).
- [x] Crear API backend para iniciar ejecución, consultar estado y leer logs.
- [x] Adaptar `attacker-sim` con `lab_runner.py` (HTTP server stdlib en puerto 8888).
- [x] Ejecutar `./run_scenario.sh <scenario>` dentro del entorno LAB, capturando
      stdout/stderr.
- [x] Al finalizar el ataque, llamar a `pipeline-worker /runs` en modo
      incremental.
- [x] Persistir logs por ejecución con límite de tamaño (50KB).
- [x] Exponer consola en vivo mediante polling (GET /lab/status cada 2s).
- [x] Invalidar/refrescar consultas de dashboard, sesiones, detalle y alertas al
      finalizar.

Pantalla web esperada:

```text
Laboratorio

[ Fuerza bruta ]       [ Reconocimiento ]
[ Descarga malware ]   [ Ataque completo ]

Estado:
queued / running / processing / completed / failed

Terminal:
[lab] iniciando escenario full
[attacker-sim] verificando Cowrie...
[attacker-sim] ejecutando brute-force...
[pipeline] events_read=...
[pipeline] alerts_sent=...
[lab] completado
```

Validación requerida:

- [x] Ejecutar cada escenario desde la app.
- [x] Confirmar eventos nuevos en PostgreSQL y Elasticsearch.
- [x] Confirmar actualización automática del dashboard y tabla de sesiones.
- [x] Confirmar alertas Telegram cuando corresponda.
- [x] Verificar bloqueo de concurrencia (test 409 en integration test).
- [x] Verificar permisos por rol (test viewer rechazado en integration test).
- [x] Verificar que un escenario inválido sea rechazado (test 400 en integration test).
- [x] Ejecutar pruebas backend/frontend/pipeline relevantes.
- [x] Ejecutar `.\scripts\validate_lab.ps1`.
- [x] Documentar evidencia en `docs/evidencias/`.

Resultados:

- Backend unit tests: 9/9 passed
- Backend integration tests: 9/9 passed
- Backend full suite: 76/76 passed
- Frontend LabView tests: 11/11 passed
- Frontend full suite: 23/23 passed
- Migración `0015_lab_runs` aplicada exitosamente

Evidencia: docs/evidencias/fase33_5_consola_lab.md

### Mejoras visuales post-implementación ✅

- **Diseño de la página Laboratorio**: rediseño completo de `LabView.tsx` con iconos
  Lucide (Lock, Eye, Bug, Zap), descripción de cada escenario, grid 2×2, badge de
  estado, banda de actividad y terminal con tipografía monospace. CSS añadido en
  `global.css` (~150 líneas) usando tokens del dashboard.
- **Template HTML del motor de reportes**: rediseño de `_html_report()` y
  `_section_rows()` en `report_service.py`. Header oscuro (`#161a1d`) con borde
  amarillo, tarjetas métricas con colores por criticidad, tablas con zebra striping
  y header teal, footer con timestamp. CSS inline, sin deps externas.

Evidencia adicional:
- docs/evidencias/fase33_5_html_report_redesign.md
- Backend: 76/76 passed (suite completa)

Skills previstos:

```text
Buscar antes de implementar:
- Docker / DevOps para runner interno y networking seguro.
- FastAPI / arquitectura backend para jobs, logs y endpoints.
- TanStack Query para polling, invalidación y estados de ejecución.
- Seguridad para evitar command injection y exposición de secretos.
- Testing frontend/backend para flujo LAB end-to-end.
```

## Fase 34 — Arquitectura segura del modo REAL

Objetivo: dejar una base segura y repetible para capturar trafico real desde
una VPS sin convertirla en requisito del proyecto y sin que Codex se conecte por
SSH a la infraestructura.

- [x] Definir una arquitectura donde la VPS actua solo como sensor Cowrie y el
      procesamiento sigue local.
- [x] Incorporar la regla operativa: Codex no se conecta por SSH; la persona con
      credenciales ejecuta `scripts/setup_vps.ps1` manualmente.
- [x] Crear `scripts/setup_vps.ps1` para preparar Ubuntu 24.04 con Docker,
      desplegar Cowrie en `/opt/oscorp-cowrie` y exponerlo en `2222`.
- [x] Crear `scripts/sync_vps_logs.ps1` para traer
      `/opt/oscorp-cowrie/logs/cowrie.json` al LAB local.
- [x] Crear `scripts/validate_real_mode.ps1` para validar scripts, perfil
      `real` y ausencia de passwords de VPS versionadas.
- [x] Actualizar `.env.example`, README y `docs/arquitectura-vps.md`.

Decision de fase:
- No se versionan IPs, passwords ni credenciales reales de DigitalOcean.
- No se toca el SSH administrativo de la VPS.
- El perfil `real` no levanta Cowrie local, `attacker-sim` ni `payload-server`.
- La prueba contra la VPS real queda para quien tiene acceso al servidor.

Evidencia: docs/evidencias/fase34_arquitectura_vps.md

## Fase 35 — Despliegue validado y sincronización continua de la VPS ✅

Objetivo: probar la base de Fase 34 contra la VPS real y automatizar la captura
continua con evidencia operativa.

- [x] Crear `scripts/setup_real.ps1` para iniciar el stack local REAL.
- [x] Parametrizar `scripts/run_n8n_pipeline.ps1` con `-Profile lab|real`.
- [x] Ajustar `scripts/sync_vps_logs.ps1 -RunPipeline` para usar perfil `real`.
- [x] Crear `scripts/run_real_sync.ps1` con intervalo, reintentos y logs.
- [x] Actualizar README con guia para entrar, iniciar y operar modo REAL.
- [x] Actualizar arquitectura y evidencia de fase.
- [x] Ejecutar `scripts/setup_vps.ps1` en la PC con credenciales VPS.
- [x] Confirmar que Cowrie recibe trafico real en la VPS de DigitalOcean (331 sesiones REAL capturadas).
- [x] Ejecutar `scripts/sync_vps_logs.ps1 -RunPipeline` y validar datos en app,
      PostgreSQL, Elasticsearch y Telegram.
- [ ] Definir rotacion/retencion de logs y procedimiento de apagado de la VPS (diferido — mejora operativa).
- [ ] Evaluar migracion de password SSH a clave SSH dedicada (diferido — mejora de seguridad).

Evidencia: docs/evidencias/fase35_operacion_vps.md

## Fase 36 — Separación y comparación LAB/REAL ✅

Objetivo: mantener trazabilidad del origen y comparar resultados.

- [x] Separar datos LAB y REAL en almacenamiento y consultas.
- [x] Etiquetar origen con campo `source_mode` ('lab'|'real') en eventos y sesiones.
- [x] Migración `0016_source_mode` con DEFAULT 'lab' y CHECK constraint.
- [x] Pipeline: `execute_pipeline(source_mode=)` propaga el modo a cada evento/sesión.
- [x] Pipeline worker: `validate_request` acepta y valida `source_mode`.
- [x] Backend API: filtro `?source_mode=lab|real` en `GET /sessions`.
- [x] Frontend: badge LAB/REAL en tabla y detalle de sesión; filtro en formulario.
- [x] Tests: 6 unit tests pipeline + 4 integration tests backend, todos verdes.
- [x] Comparar ataques simulados con tráfico real — 331 sesiones REAL + datos LAB coexisten en la app; filtro `?source_mode=` operativo y validado.
- [x] Documentar diferencias, sesgos y limitaciones observadas — registrado en docs/evidencias/fase36_separacion_lab_real.md.

## Fase 37 — Pruebas automatizadas y CI ✅

Objetivo: establecer controles continuos de calidad.

- [x] Agregar pruebas unitarias, integración y end-to-end.
- [x] Configurar lint (ruff), validación de Docker Compose.
- [x] Crear pipeline CI sin secretos reales (`.github/workflows/ci.yml`, 6 jobs).
- [x] Definir una línea base de cobertura y fallos bloqueantes (60 %, `--cov-fail-under=60`).

## Fase 38 — Reproducibilidad y revisión de seguridad final ✅

Objetivo: validar una entrega instalable y defendible.

```text
[x] Validar instalación desde otra máquina limpia.
    validate_reproducibility.ps1 — auditoría integral de reproducibilidad y seguridad.

[x] Probar backup y restauración completos.
    backup.ps1 actualizado con --clean --if-exists.
    restore.ps1 creado — restaura PostgreSQL, re-indexa Elasticsearch.
    Ciclo backup→restore validado: 1879 eventos, 331 sesiones, 51 runs restaurados sin pérdida.

[x] Revisar dependencias, secretos, privacidad y retención de datos.
    test_security_audit.py — 13 tests automatizados de auditoría.
    Resultado: 13/13 OK. Ver docs/evidencias/fase38_reproducibilidad_seguridad.md.
    Riesgos conocidos documentados y aceptados.

[x] Crear una versión etiquetada del sistema.
    git tag v1.0.0 — primera entrega completa del sistema.
```

Evidencia: docs/evidencias/fase38_reproducibilidad_seguridad.md

## Fase 39 — Documentación, defensa y actualización de tesis

Objetivo: cerrar el proyecto académico después de finalizar el sistema.

- [ ] Crear el diagrama final de arquitectura y actualizar las guías.
- [ ] Crear video demo y consolidar evidencias y métricas.
- [ ] Registrar diferencias entre el sistema original y OSCORP ThreatLab.
- [ ] Actualizar el PDF de la tesis con arquitectura, metodología y resultados definitivos.

---

# Historial técnico de la reestructuración

## Separación entre modo LAB local reproducible y modo REAL con VPS

## Separación entre modo LAB local reproducible y modo REAL con VPS

## Objetivo general de la refactorización

[x] Reestructurar el sistema original de la tesis para que no dependa obligatoriamente de una VPS.
[x] Separar el proyecto en dos modos de funcionamiento:

```text
Modo LAB / Local:
Sistema completo ejecutado en la PC mediante Docker Compose.
Permite pruebas locales reproducibles sin pagar VPS ni exponer servicios a internet.

Modo REAL / VPS:
Cowrie se ejecuta en una VPS pública para capturar tráfico real.
El procesamiento se mantiene separado y reutiliza el mismo pipeline.
```

[x] Mantener el flujo original del proyecto, pero ordenado para soportar ambos escenarios:

```text
Cowrie → cowrie.json → n8n → PostgreSQL → Elasticsearch → Kibana → Telegram/API enrichment
```

---

# Fase 1 — Creación del proyecto y estructura base

## Tareas realizadas

[x] Se creó la carpeta principal del proyecto:

```text
oscorp-honeypot-lab
```

[x] Se inicializó/organizó el proyecto como una base limpia para el nuevo sistema refactorizado.

[x] Se definió una estructura modular de carpetas para separar componentes:

```text
oscorp-honeypot-lab/
│
├── docker-compose.yml
├── .env.example
├── .env
├── README.md
│
├── cowrie/
│   ├── etc/
│   └── logs/
│
├── n8n/
│   └── workflows/
│
├── postgres/
│   └── init.sql
│
├── elasticsearch/
│
├── kibana/
│
├── attacker-sim/
│   ├── Dockerfile
│   ├── run_scenario.sh
│   ├── passwords.txt
│   └── scenarios/
│
├── scripts/
│
└── docs/
```

[x] Se dejó preparada la estructura para que el proyecto pueda documentarse, versionarse y reproducirse desde cero.

## Resultado de la fase

[x] Proyecto base creado correctamente.
[x] Estructura inicial compatible con la separación LAB/VPS.

---

# Fase 2 — Variables de entorno y configuración inicial

## Tareas realizadas

[x] Se creó el archivo `.env.example`.

[x] Se definieron variables para PostgreSQL:

```env
POSTGRES_DB=oscorp
POSTGRES_USER=oscorp
POSTGRES_PASSWORD=oscorp123
POSTGRES_PORT=5433
```

[x] Se definieron variables para n8n:

```env
N8N_PORT=5678
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=admin123
```

[x] Se definieron variables para Elasticsearch y Kibana:

```env
ELASTICSEARCH_PORT=9200
KIBANA_PORT=5601
```

[x] Se definió el puerto local de Cowrie:

```env
COWRIE_SSH_PORT=2222
```

[x] Se reservaron variables para futuras integraciones:

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
VIRUSTOTAL_API_KEY=
```

[x] Se reservaron variables para el modo VPS:

```env
VPS_HOST=
VPS_USER=
VPS_COWRIE_LOG_PATH=
```

[x] Se copió `.env.example` a `.env`.

## Resultado de la fase

[x] Variables de entorno creadas correctamente.
[x] Configuración preparada para modo LAB y modo REAL.
[x] No se detectaron errores en esta fase.

---

# Fase 3 — Creación de Docker Compose con perfiles LAB y REAL

## Tareas realizadas

[x] Se creó el archivo `docker-compose.yml`.

[x] Se definieron servicios comunes para ambos modos:

```text
postgres
elasticsearch
kibana
n8n
```

[x] Se definieron servicios exclusivos del modo LAB:

```text
cowrie
attacker-sim
```

[x] Se configuró PostgreSQL con imagen:

```text
postgres:16
```

[x] Se configuró Elasticsearch con imagen:

```text
docker.elastic.co/elasticsearch/elasticsearch:8.13.4
```

[x] Se configuró Kibana con imagen:

```text
docker.elastic.co/kibana/kibana:8.13.4
```

[x] Se configuró n8n con imagen:

```text
n8nio/n8n:latest
```

[x] Se configuró Cowrie inicialmente con imagen:

```text
cowrie/cowrie:latest
```

[x] Se configuró el servicio `attacker-sim` con build local desde:

```text
./attacker-sim/Dockerfile
```

[x] Se creó la red Docker:

```text
oscorp_net
```

[x] Se crearon volúmenes persistentes para:

```text
postgres_data
elasticsearch_data
n8n_data
```

[x] Se creó el archivo `postgres/init.sql`.

[x] Se definió la tabla principal de eventos:

```text
eventos
```

[x] Se definió la tabla para auditoría de ejecuciones del pipeline:

```text
pipeline_runs
```

[x] Se definió la tabla para alertas y futura medición real de MTTD:

```text
alerts
```

[x] Se crearon carpetas necesarias:

```text
cowrie/logs
cowrie/etc
n8n/workflows
attacker-sim/scenarios
```

[x] Se creó el archivo:

```text
attacker-sim/Dockerfile
```

[x] Se creó el archivo:

```text
attacker-sim/passwords.txt
```

[x] Se crearon archivos base para futuros escenarios de ataque:

```text
attacker-sim/run_scenario.sh
attacker-sim/scenarios/brute_force.sh
attacker-sim/scenarios/recon.sh
attacker-sim/scenarios/malware_download.sh
attacker-sim/scenarios/full_attack.sh
```

## Verificaciones realizadas

[x] Se ejecutó:

```powershell
docker compose config
```

Resultado observado:

```text
services: {}
```

[x] Se verificó que ese resultado no era un error, porque todos los servicios están asociados a perfiles.

[x] Se ejecutó:

```powershell
docker compose --profile lab config
```

[x] Se confirmó que el perfil LAB incluye:

```text
postgres
elasticsearch
kibana
n8n
cowrie
attacker-sim
```

[x] Se ejecutó:

```powershell
docker compose --profile real config
```

[x] Se confirmó que el perfil REAL incluye:

```text
postgres
elasticsearch
kibana
n8n
```

[x] Se confirmó que el perfil REAL no incluye:

```text
cowrie
attacker-sim
```

## Resultado de la fase

[x] Docker Compose quedó correctamente dividido en perfiles.
[x] El modo LAB y el modo REAL quedaron separados desde la configuración.
[x] No hubo errores estructurales en el YAML.
[x] La salida `services: {}` sin perfil fue validada como comportamiento esperado.

---

# Fase 4 — Levantamiento del modo LAB local

## Tareas realizadas

[x] Se levantó el entorno local con:

```powershell
docker compose --profile lab up -d
```

[x] Se verificó que los servicios principales quedaran creados.

[x] Se verificaron los contenedores esperados:

```text
oscorp_postgres
oscorp_elasticsearch
oscorp_kibana
oscorp_n8n
oscorp_cowrie
oscorp_attacker_sim
```

[x] Se validó PostgreSQL.

[x] Se validó Elasticsearch.

[x] Se validó Kibana.

[x] Se validó n8n.

[x] Se validó el contenedor `attacker-sim`.

## Problema detectado

[x] Se detectó un error en Cowrie al revisar los logs:

```text
FileNotFoundError:
No such file or directory:
'/cowrie/cowrie-git/src/cowrie/data/honeyfs/etc/passwd'
```

[x] También apareció el error:

```text
Unknown command: cowrie
```

## Diagnóstico

[x] Se identificó que el problema estaba asociado al servicio Cowrie y no al resto del stack.

[x] Se identificó que el uso de:

```yaml
image: cowrie/cowrie:latest
```

no era recomendable para reproducibilidad.

[x] Se identificó que montar la carpeta local vacía:

```yaml
./cowrie/etc:/cowrie/cowrie-git/etc
```

podía interferir con la configuración interna del contenedor.

## Correcciones aplicadas

[x] Se detuvo el entorno LAB.

[x] Se reemplazó la imagen de Cowrie:

```yaml
image: cowrie/cowrie:latest
```

por una versión fija:

```yaml
image: cowrie/cowrie:3.0.0
```

[x] Se eliminó el volumen problemático:

```yaml
- ./cowrie/etc:/cowrie/cowrie-git/etc
```

[x] El servicio Cowrie quedó configurado solo con el volumen de logs:

```yaml
volumes:
  - ./cowrie/logs:/cowrie/cowrie-git/var/log/cowrie
```

[x] Se eliminó/recreó el contenedor anterior de Cowrie.

[x] Se descargó la imagen fija:

```powershell
docker pull cowrie/cowrie:3.0.0
```

[x] Se levantó nuevamente el modo LAB.

## Verificación posterior a la corrección

[x] Cowrie inició correctamente.

[x] Cowrie quedó en estado `Up`.

[x] Cowrie expuso correctamente el puerto SSH local:

```text
localhost:2222
```

[x] Se realizó conexión SSH manual a Cowrie:

```powershell
ssh root@localhost -p 2222
```

[x] Se generó correctamente el archivo:

```text
cowrie/logs/cowrie.json
```

## Resultado de la fase

[x] Modo LAB levantado correctamente.
[x] PostgreSQL funcionando.
[x] Elasticsearch funcionando.
[x] Kibana funcionando.
[x] n8n funcionando.
[x] attacker-sim preparado.
[x] Cowrie funcionando luego de la corrección.
[x] Se corrigió el uso de `latest`, mejorando la reproducibilidad del sistema.

---

# Fase 5 — Estabilización de Cowrie local y preparación del log para n8n

## Tareas realizadas

[x] Se confirmó que Cowrie genera el archivo principal de eventos:

```text
cowrie/logs/cowrie.json
```

[x] Se confirmó que el archivo `cowrie.json` contiene eventos generados por Cowrie.

[x] Se validó que el sensor local funciona en modo LAB sin VPS.

[x] Se confirmó que el flujo inicial del modo LAB ya tiene sensor operativo:

```text
Conexión SSH local → Cowrie → cowrie.json
```

[x] Se confirmó que el archivo generado será la fuente que leerá n8n.

[x] Se dejó establecido que dentro del contenedor n8n el log debe leerse desde:

```text
/files/cowrie/cowrie.json
```

[x] Se dejó preparado el camino para que el workflow de n8n procese eventos desde el log local.

## Resultado de la fase

[x] Cowrie local estabilizado.
[x] `cowrie.json` generado correctamente.
[x] Sensor LAB validado.
[x] El proyecto ya puede generar evidencia local sin usar VPS.
[x] La base para la prueba reproducible local quedó lista.

---

# Estado actual del proyecto después de la Fase 5

[x] El proyecto tiene estructura modular.
[x] El proyecto tiene variables de entorno.
[x] Docker Compose tiene perfiles separados.
[x] El perfil LAB levanta el entorno local.
[x] El perfil REAL queda reservado para pruebas con VPS.
[x] Cowrie funciona localmente.
[x] Cowrie genera `cowrie.json`.
[x] PostgreSQL está preparado para recibir eventos.
[x] Elasticsearch está preparado para indexar eventos.
[x] Kibana está preparado para visualizar eventos.
[x] n8n está preparado para leer el log de Cowrie.
[x] attacker-sim está creado, pero todavía no configurado completamente.

---

# Siguiente etapa

# Fase 6 — Configurar attacker-sim y escenarios de ataque reproducibles

## Objetivo de la Fase 6

Configurar el contenedor atacante para simular ataques completos contra Cowrie dentro del entorno Docker, sin usar VPS, sin internet real y sin intervención manual.

El objetivo es poder ejecutar comandos como:

```powershell
docker compose run --rm attacker-sim ./run_scenario.sh brute-force
docker compose run --rm attacker-sim ./run_scenario.sh recon
docker compose run --rm attacker-sim ./run_scenario.sh malware-download
docker compose run --rm attacker-sim ./run_scenario.sh full
```

---

## Tareas realizadas de la Fase 6

[x] Completar el archivo:

```text
attacker-sim/run_scenario.sh
```

[x] Completar el escenario de fuerza bruta:

```text
attacker-sim/scenarios/brute_force.sh
```

[x] Completar el escenario de reconocimiento post-login:

```text
attacker-sim/scenarios/recon.sh
```

[x] Completar el escenario de descarga simulada:

```text
attacker-sim/scenarios/malware_download.sh
```

[x] Completar el escenario de ataque completo:

```text
attacker-sim/scenarios/full_attack.sh
```

[x] Verificar que `attacker-sim` pueda resolver el hostname interno:

```text
cowrie
```

[x] Verificar conectividad desde `attacker-sim` hacia Cowrie:

```text
cowrie:2222
```

[x] Ejecutar el escenario de fuerza bruta.

[x] Confirmar que Cowrie registra eventos:

```text
cowrie.login.failed
cowrie.login.success
```

[x] Ejecutar el escenario de reconocimiento.

[x] Confirmar que Cowrie registra eventos:

```text
cowrie.command.input
```

[x] Ejecutar el escenario de descarga simulada.

[x] Confirmar que Cowrie registra eventos:

```text
cowrie.session.file_download
```

[x] Ejecutar el escenario completo:

```text
full
```

[x] Confirmar que `cowrie.json` contiene una secuencia completa de ataque:

```text
conexión
intentos de login
login exitoso
comandos
descargas
cierre de sesión
```

[x] Guardar evidencia del log generado en:

```text
docs/evidencias/
```

[x] Documentar la Fase 6 como validación del modo LAB reproducible.

## Verificación realizada

[x] Se ejecutó:

```powershell
docker compose --profile lab run --rm attacker-sim ./run_scenario.sh full
```

[x] Se generaron 107 eventos nuevos en `cowrie/logs/cowrie.json`.

[x] Se confirmó la presencia de:

```text
cowrie.login.failed
cowrie.login.success
cowrie.command.input
cowrie.session.file_download
```

[x] Se guardó evidencia en:

```text
docs/evidencias/fase6_attacker_sim.md
docs/evidencias/cowrie_lab_fase6.json
```

## Nota técnica

[x] Para generar `cowrie.session.file_download`, Cowrie 3.0.0 registró correctamente descargas desde `http://example.com`.

[x] Los intentos usando IP privada Docker o alias `attacker-sim` quedaron registrados como comandos, pero no generaron `cowrie.session.file_download` porque el entorno emulado de Cowrie no resolvió esos destinos.

---

# Resultado esperado al finalizar la Fase 6

[x] El sistema podrá generar ataques reproducibles localmente.
[x] El evaluador no necesitará una VPS para validar el funcionamiento del proyecto.
[x] El modo LAB quedará como entorno principal de prueba académica.
[x] El modo REAL/VPS quedará como extensión opcional para tráfico real.
[x] El trabajo final de tesis podrá presentar claramente dos modalidades:

```text
Modo LAB:
Reproducible, local, gratuito y controlado.

Modo REAL:
Expuesto a internet, con tráfico real y dependiente de VPS.
```

---

# Fase 7 — Pipeline local reproducible hacia PostgreSQL y Elasticsearch

## Objetivo de la Fase 7

Procesar el archivo `cowrie/logs/cowrie.json` generado por Cowrie en modo LAB y persistir los eventos en PostgreSQL e Elasticsearch, manteniendo la trazabilidad del flujo original:

```text
Cowrie → cowrie.json → procesamiento → PostgreSQL → Elasticsearch → Kibana/n8n
```

En esta reestructuración, la Fase 7 se enfocó primero en el pipeline local reproducible. La exposición VPS del modo REAL queda reservada para una fase posterior.

## Correcciones de fases anteriores

[x] Se corrigió el uso de `n8nio/n8n:latest`.

```yaml
image: n8nio/n8n:${N8N_VERSION:-2.15.0}
```

[x] Se agregó `N8N_VERSION=2.15.0` a `.env.example`.

[x] Se agregó `.gitignore` para evitar versionar `.env`, datos vivos y logs runtime.

[x] Se corrigió el modelo de persistencia de eventos.

Problema detectado:

```text
event_uuid TEXT UNIQUE
```

Motivo:

```text
Cowrie puede repetir el campo uuid en múltiples eventos de una sesión.
```

Corrección aplicada:

```text
event_hash TEXT UNIQUE
```

`event_hash` se calcula como SHA-256 de cada línea NDJSON, permitiendo ingesta idempotente sin perder eventos.

[x] Se actualizó `postgres/init.sql` para crear índices sobre:

```text
event_hash
event_uuid
eventid
session_id
src_ip
timestamp_evento
```

[x] Se corrigió el README para que refleje archivos y comandos reales del proyecto.

[x] Se completaron documentos base:

```text
docs/arquitectura-local.md
docs/arquitectura-vps.md
docs/guia-demo.md
```

## Tareas realizadas

[x] Se creó el procesador:

```text
scripts/process_cowrie_ndjson.py
```

[x] Se creó wrapper PowerShell:

```text
scripts/run_pipeline.ps1
```

[x] Se creó workflow importable de referencia para n8n:

```text
n8n/workflows/oscorp-workflow.json
```

[x] Se importó correctamente el workflow en n8n como workflow inactivo.

[x] Se procesó el log actual:

```powershell
.\scripts\run_pipeline.ps1
```

[x] Se insertaron/indexaron eventos en:

```text
PostgreSQL → tabla eventos
Elasticsearch → índice cowrie-events
```

[x] Se registró la ejecución del pipeline en:

```text
pipeline_runs
```

## Verificaciones realizadas

[x] PostgreSQL contiene:

```text
366 eventos
366 event_hash únicos
48 sesiones
```

[x] Elasticsearch contiene:

```text
366 documentos en cowrie-events
```

[x] Eventos principales confirmados:

```text
64 cowrie.command.input
48 cowrie.session.connect
48 cowrie.session.closed
42 cowrie.client.version
42 cowrie.client.kex
36 cowrie.login.success
32 cowrie.session.params
32 cowrie.log.closed
8  cowrie.session.file_download
4  cowrie.login.failed
2  cowrie.command.failed
```

[x] Se reejecutó el pipeline para confirmar idempotencia:

```text
PostgreSQL se mantuvo en 366 eventos únicos.
Elasticsearch se mantuvo en 366 documentos.
```

[x] Se guardó evidencia en:

```text
docs/evidencias/fase7_pipeline_local.md
```

## Resultado de la fase

[x] Pipeline local funcionando.
[x] Persistencia PostgreSQL validada.
[x] Indexación Elasticsearch validada.
[x] Ingesta idempotente validada.
[x] Workflow n8n de referencia importado.
[x] Documentación base corregida.
[x] Errores de versión y modelo de datos detectados y corregidos.
