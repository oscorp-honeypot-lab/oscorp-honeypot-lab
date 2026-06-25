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
24 de junio de 2026
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
Aplicación web propia:                      No implementada
Attack Risk Score:                          No implementado
Alertas Telegram y MTTD real:               No implementados en la reestructuración
VirusTotal e ip-api:                        No implementados en la reestructuración
Reportes automáticos:                       No implementados
Modo REAL/VPS:                              Diseñado, no validado
Pruebas automatizadas/CI:                   No implementadas
Actualización final de la tesis:            Pendiente hasta finalizar el sistema
```

## Última evidencia operativa disponible

Última validación: **25 de junio de 2026**.

La validación operativa de la Fase 10 confirmó:

```text
- ocho servicios persistentes del perfil LAB operativos;
- configuración Docker Compose válida;
- PostgreSQL y Elasticsearch sincronizados en 1496 registros;
- revisión Alembic 0001_initial_schema aplicada y en head;
- diez scripts PowerShell sin errores de sintaxis;
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
- clon limpio finalizado con 105 eventos, 15 sesiones y 0 duplicados.
```

Se verificaron los ocho servicios persistentes del perfil LAB en ejecución:

```text
oscorp_cowrie
oscorp_attacker_sim
oscorp_postgres
oscorp_elasticsearch
oscorp_kibana
oscorp_n8n
oscorp_pipeline_worker
oscorp_payload_server
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
```

Se ejecutó el smoke test completo:

```powershell
.\scripts\smoke_test.ps1 -NoBuild
```

Resultado:

```text
[validate] LAB válido
[demo] Flujo completo validado
[demo] Eventos nuevos en PostgreSQL: 104
[demo] Total acumulado: 1496
[smoke] Prueba integral superada
```

Validación decisiva de reproducibilidad:

```text
Origen: clon local nuevo del commit de Fase 8
Estado inicial: sin .env y con volúmenes Docker vacíos
Comando: .\scripts\smoke_test.ps1

Alembic: 0001_initial_schema aplicado correctamente
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
Primera ejecución n8n:
- run_id=57
- events_read=422
- events_inserted=104
- events_indexed=422
- errors_count=0

Segunda ejecución n8n:
- run_id=58
- events_read=422
- events_inserted=0
- events_indexed=422
- errors_count=0
```

Estado acumulado de la validación más reciente:

```text
PostgreSQL:
- 1496 eventos
- 1496 event_hash únicos
- 260 sesiones
- 26 ejecuciones en pipeline_runs
- último run_id: 58
- último evento: 2026-06-25 07:05:39.936686

Elasticsearch:
- 1496 documentos en cowrie-events

n8n:
- versión efectiva 2.15.0
- 2 credenciales nativas importadas y cifradas
- workflow OSCORP ejecutado punta a punta

pipeline-worker:
- contrato 1.0
- servicio privado sin puerto publicado
- ejecución concurrente protegida por lock

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
- Base adecuada para construir una capa analítica propia.

## Riesgos y deuda técnica actuales

### Críticos

- No existe todavía la aplicación/dashboard propio que constituye la principal diferenciación de la reestructuración.

### Altos

- PostgreSQL, Elasticsearch, Kibana y n8n publican puertos con configuración de laboratorio y credenciales por defecto.
- El workflow n8n continúa manual e inactivo; la programación corresponde a la Fase 11.
- Cada ejecución todavía relee el NDJSON completo; falta cursor/checkpoint incremental.
- El modo `real` todavía no aplica endurecimiento, autenticación ni separación de secretos suficiente para exposición pública.
- La imagen `attacker-sim` es grande por las dependencias de Hydra y puede optimizarse en una fase de rendimiento.

### Medios

- No existen tests automáticos del parser, normalización, idempotencia o escenarios.
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

- [ ] Diseñar cursor, offset o checkpoint persistente.
- [ ] Evitar reprocesamiento después de reinicios.
- [ ] Definir recuperación cuando cambia o se rota `cowrie.json`.
- [ ] Probar ejecuciones sucesivas sin duplicados ni pérdida de eventos.

## Fase 12 — Trazabilidad y recuperación del pipeline

Objetivo: hacer observable y resistente la orquestación.

- [ ] Registrar cada ejecución en `pipeline_runs`.
- [ ] Manejar eventos inválidos y errores parciales.
- [ ] Agregar reintentos controlados y estados finales claros.
- [ ] Validar fallos y recuperación punta a punta con evidencia.

## Fase 13 — Modelo de sesiones correlacionadas

Objetivo: construir la unidad analítica principal del sistema.

- [ ] Diseñar la entidad, tabla o vista de sesiones.
- [ ] Agrupar eventos por `session_id`.
- [ ] Calcular inicio, fin, duración y resumen de actividad.
- [ ] Crear la migración y validar sesiones completas e incompletas.

## Fase 14 — Reglas versionadas de Attack Risk Score

Objetivo: definir el modelo de puntuación propio sin acoplarlo a la interfaz.

- [ ] Definir reglas, pesos, versión y límites del score.
- [ ] Incluir login exitoso, usuarios privilegiados, reconocimiento, descarga y persistencia.
- [ ] Reservar señales para reputación de hashes y origen cloud.
- [ ] Definir niveles Bajo, Medio, Alto y Crítico.

```text
0-20:  Bajo
21-50: Medio
51-80: Alto
81+:   Crítico
```

## Fase 15 — Cálculo, persistencia y pruebas del Risk Score

Objetivo: aplicar el score a sesiones reales de forma auditable.

- [ ] Calcular el score por sesión.
- [ ] Registrar los motivos y la versión de reglas utilizada.
- [ ] Permitir recalcular sesiones al cambiar las reglas.
- [ ] Crear pruebas unitarias y casos límite.

## Fase 16 — Base arquitectónica de la API

Objetivo: crear el backend de OSCORP ThreatLab con límites claros.

- [ ] Crear el servicio FastAPI con Python 3.12, Pydantic v2 y configuración tipada.
- [ ] Aplicar un monolito modular con `domain`, `application`, `adapters`, `infrastructure` y `api`.
- [ ] Configurar SQLAlchemy 2 asíncrono, psycopg 3 y una única cadena de migraciones Alembic.
- [ ] Contenerizar el backend y exponer healthcheck, logs estructurados y OpenAPI.

## Fase 17 — Identidad y seguridad de la aplicación

Objetivo: proteger la aplicación antes de exponer operaciones y datos.

- [ ] Crear usuarios, roles `viewer`, `analyst` y `admin`, y registro de auditoría.
- [ ] Implementar Argon2id y sesiones de servidor con cookies HttpOnly, SameSite y Secure en producción.
- [ ] Implementar CSRF, CORS por allowlist, rate limiting y cabeceras de seguridad.
- [ ] Proteger endpoints por permisos y probar autenticación, autorización, cierre y expiración de sesión.
- [ ] Mantener secretos fuera de Git y evitar tokens de acceso en `localStorage`.

## Fase 18 — API de consulta analítica

Objetivo: exponer los datos principales para el dashboard.

- [ ] Crear endpoint de resumen general.
- [ ] Crear listado paginado de sesiones y eventos.
- [ ] Crear detalle de sesión con comandos, descargas y score.
- [ ] Agregar pruebas de integración de lectura.

## Fase 19 — API de filtros y revisión operativa

Objetivo: soportar el trabajo de análisis sobre las sesiones.

- [ ] Filtrar por tiempo, IP, país, usuario, evento y criticidad.
- [ ] Permitir marcar y desmarcar sesiones como revisadas.
- [ ] Registrar fecha y estado de revisión.
- [ ] Probar filtros combinados y transiciones de estado.

## Fase 20 — API de exportación

Objetivo: permitir extraer datos sin depender de Kibana.

- [ ] Exportar sesiones y eventos filtrados a CSV.
- [ ] Definir límites y paginación para exportaciones grandes.
- [ ] Registrar errores y metadatos de la exportación.
- [ ] Agregar pruebas de contenido y codificación.

## Fase 21 — Base React y dashboard operativo

Objetivo: crear la primera interfaz propia utilizable.

- [ ] Crear React + TypeScript + Vite con rutas, layout operativo y control de sesión.
- [ ] Generar el cliente TypeScript desde OpenAPI y consumirlo con TanStack Query.
- [ ] Crear resumen, evolución temporal y distribución de riesgo con Apache ECharts.
- [ ] Crear tabla de sesiones con TanStack Table, filtros, paginación y ordenamiento.
- [ ] Definir componentes accesibles, diseño responsive y estados de carga, vacío y error.

## Fase 22 — Detalle interactivo de sesión

Objetivo: completar el flujo principal de análisis.

- [ ] Mostrar timeline, eventos, comandos y descargas.
- [ ] Mostrar Risk Score y motivos.
- [ ] Mostrar alertas asociadas a la sesión.
- [ ] Permitir marcar la sesión como revisada.
- [ ] Mantener Kibana como herramienta complementaria.

## Fase 23 — Modelo y políticas de alertas

Objetivo: definir qué genera una alerta y cómo se registra.

- [ ] Completar la tabla `alerts` mediante migración.
- [ ] Incluir `event_hash`, `session_id`, timestamps, MTTD, canal, estado y error.
- [ ] Definir criterios de alerta por evento, sesión y criticidad.
- [ ] Registrar timestamps de evento y procesamiento.
- [ ] Definir estados, canal y detalle de error.

## Fase 24 — Entrega de alertas por Telegram

Objetivo: enviar alertas y registrar su resultado real.

- [ ] Integrar Telegram mediante un adaptador configurable.
- [ ] Gestionar token y destino sin versionar secretos.
- [ ] Registrar envíos exitosos y fallidos.
- [ ] Agregar reintentos controlados y pruebas.

## Fase 25 — Medición real de MTTD

Objetivo: reemplazar la estimación teórica por métricas evento-alerta.

- [ ] Calcular `alert_sent_timestamp - event_timestamp`.
- [ ] Obtener promedio, mínimo, máximo y percentil 95.
- [ ] Calcular latencia por tipo de evento y porcentaje de fallos.
- [ ] Exponer las métricas en API y dashboard.

## Fase 26 — Enriquecimiento geográfico de IPs

Objetivo: contextualizar el origen de las conexiones.

- [ ] Integrar ip-api mediante un adaptador.
- [ ] Agregar caché para evitar consultas repetidas.
- [ ] Guardar país, ciudad, ISP, ASN, latitud y longitud.
- [ ] Registrar expiración, errores y límites de consulta.

## Fase 27 — Enriquecimiento de hashes con VirusTotal

Objetivo: contextualizar los archivos descargados.

- [ ] Integrar VirusTotal mediante un adaptador.
- [ ] Consultar hashes sin subir payloads.
- [ ] Guardar resultado, fecha de consulta y errores.
- [ ] Agregar caché, límites y gestión segura de la API key.

## Fase 28 — Enriquecimiento aplicado al Risk Score

Objetivo: incorporar contexto externo sin volver inestable el score.

- [ ] Agregar reputación del hash y origen cloud a las reglas.
- [ ] Definir comportamiento cuando el enriquecimiento falta o está vencido.
- [ ] Recalcular sesiones afectadas.
- [ ] Crear pruebas para respuestas externas parciales o fallidas.

## Fase 29 — Visualización geográfica

Objetivo: representar actividad por ubicación.

- [ ] Definir el mapeo `geo_point` en Elasticsearch.
- [ ] Crear el mapa geográfico en Kibana.
- [ ] Crear la visualización equivalente en la aplicación propia.
- [ ] Validar sesiones sin coordenadas o con datos incompletos.

## Fase 30 — Motor de reportes periódicos

Objetivo: generar conjuntos de datos diarios y semanales.

- [ ] Calcular eventos, IPs, sesiones, países, credenciales y comandos principales.
- [ ] Incluir archivos, hashes maliciosos, sesiones críticas, MTTD y alertas fallidas.
- [ ] Programar reportes diarios y semanales.
- [ ] Validar resultados contra consultas directas.

## Fase 31 — Formatos y entrega de reportes

Objetivo: distribuir reportes reproducibles.

- [ ] Generar HTML o PDF y CSV.
- [ ] Permitir descarga desde la aplicación.
- [ ] Permitir envío por Telegram.
- [ ] Registrar generación, entrega y errores.

## Fase 32 — Dashboards operativos de Kibana

Objetivo: crear una capa complementaria para operación y tiempo.

- [ ] Crear el data view de `cowrie-events`.
- [ ] Crear paneles de eventos, sesiones y evolución temporal.
- [ ] Crear filtros y tablas operativas.
- [ ] Validar los paneles con datos LAB.

## Fase 33 — Dashboards analíticos de Kibana versionados

Objetivo: completar y volver importable la capa Kibana.

- [ ] Crear visualizaciones de riesgo y mapa geográfico.
- [ ] Exportar objetos a `kibana/dashboards.ndjson`.
- [ ] Automatizar o documentar la importación.
- [ ] Validar exportación e importación desde una instancia limpia.

## Fase 34 — Arquitectura segura del modo REAL

Objetivo: diseñar la captura pública sin convertir la VPS en requisito.

- [ ] Definir una arquitectura que no dependa de la PC local encendida.
- [ ] Crear modelo de amenazas y endurecimiento de Cowrie.
- [ ] Definir cifrado, autenticación y gestión de secretos.
- [ ] Documentar costos, límites y responsabilidades del modo REAL.

## Fase 35 — Despliegue y sincronización de la VPS

Objetivo: automatizar la captura y el envío continuo.

- [ ] Automatizar instalación y actualización de Cowrie.
- [ ] Implementar sincronización o envío continuo de eventos.
- [ ] Agregar buffer, reintentos y recuperación ante desconexiones.
- [ ] Validar el flujo sin exponer los servicios internos del LAB.

## Fase 36 — Separación y comparación LAB/REAL

Objetivo: mantener trazabilidad del origen y comparar resultados.

- [ ] Separar datos LAB y REAL en almacenamiento y consultas.
- [ ] Etiquetar origen, sensor y ambiente.
- [ ] Comparar ataques simulados con tráfico real.
- [ ] Documentar diferencias, sesgos y limitaciones.

## Fase 37 — Pruebas automatizadas y CI

Objetivo: establecer controles continuos de calidad.

- [ ] Agregar pruebas unitarias, integración y end-to-end.
- [ ] Configurar lint, validación de migraciones y Docker Compose.
- [ ] Crear pipeline CI sin secretos reales.
- [ ] Definir una línea base de cobertura y fallos bloqueantes.

## Fase 38 — Reproducibilidad y revisión de seguridad final

Objetivo: validar una entrega instalable y defendible.

- [ ] Validar instalación desde otra máquina limpia.
- [ ] Probar backup y restauración completos.
- [ ] Revisar dependencias, secretos, privacidad y retención de datos.
- [ ] Crear una versión etiquetada del sistema.

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
