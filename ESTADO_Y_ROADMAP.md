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

---

# Estado ejecutivo actual

## Fecha de revisión

```text
24 de junio de 2026
```

## Estado resumido

```text
Estructura Docker LAB/REAL:                 Implementada
Cowrie local:                               Implementado y validado el 24/06/2026
Simulación de ataques:                      Implementada y validada el 24/06/2026
Persistencia PostgreSQL:                    Implementada y validada el 24/06/2026
Indexación Elasticsearch:                  Implementada y validada el 24/06/2026
Ingesta idempotente por event_hash:         Implementada y validada el 24/06/2026
Workflow n8n:                               Importado, inactivo y no validado punta a punta
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

Última validación: **24 de junio de 2026**.

Se verificaron los seis servicios del perfil LAB en ejecución:

```text
oscorp_cowrie
oscorp_attacker_sim
oscorp_postgres
oscorp_elasticsearch
oscorp_kibana
oscorp_n8n
```

Estado de servicios:

```text
PostgreSQL:    acepta conexiones
Elasticsearch: operativo, estado yellow esperado en nodo único
Kibana:        available
n8n:           versión efectiva 2.15.0
Cowrie:        accesible desde attacker-sim en cowrie:2222
```

Se ejecutó una campaña completa:

```powershell
docker compose --profile lab run --rm attacker-sim ./run_scenario.sh full
```

La campaña generó 106 eventos nuevos entre:

```text
2026-06-24T19:51:20.739091Z
2026-06-24T19:51:40.663607Z
```

Se procesaron con:

```powershell
.\scripts\run_pipeline.ps1
```

Resultado de la ejecución:

```text
events_read=106
events_inserted=106
elasticsearch_indexed=106
status=completed
```

Estado acumulado:

```text
PostgreSQL:
- 472 eventos
- 472 event_hash únicos
- 63 sesiones
- último evento: 2026-06-24 19:51:40.663607

Elasticsearch:
- 472 documentos en cowrie-events

n8n:
- versión efectiva 2.15.0
- workflow OSCORP importado como inactivo

Kibana:
- estado general available
```

Distribución acumulada principal:

```text
78 cowrie.command.input
63 cowrie.session.connect
63 cowrie.session.closed
56 cowrie.client.kex
56 cowrie.client.version
46 cowrie.login.success
41 cowrie.session.params
41 cowrie.log.closed
10 cowrie.session.file_download
9  cowrie.client.size
6  cowrie.login.failed
3  cowrie.command.failed
```

Evidencia asociada:

```text
docs/evidencias/validacion_operativa_2026-06-24.md
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

- El repositorio Git todavía no tiene una línea base limpia: casi todo el proyecto continúa sin seguimiento en el commit actual.
- El pipeline realmente validado se ejecuta mediante Python desde el host y no mediante n8n punta a punta.
- El workflow n8n contiene una credencial placeholder y permanece inactivo.
- No existe todavía la aplicación/dashboard propio que constituye la principal diferenciación de la reestructuración.

### Altos

- La ejecución depende de Python instalado en el host; aún no existe un flujo totalmente encapsulado en Docker.
- `run_pipeline.ps1` contiene una ruta local específica como primera opción, aunque posee fallback a `python`.
- El escenario `malware-download` usa `example.com` por defecto para provocar `cowrie.session.file_download`; por lo tanto no es completamente offline.
- No existen migraciones formales de base de datos; `init.sql` y el procesador realizan ajustes de esquema.
- No hay healthchecks ni esperas de disponibilidad entre servicios.
- PostgreSQL, Elasticsearch, Kibana y n8n publican puertos con configuración de laboratorio y credenciales por defecto.
- El modo `real` todavía no aplica endurecimiento, autenticación ni separación de secretos suficiente para exposición pública.

### Medios

- No existen tests automáticos del parser, normalización, idempotencia o escenarios.
- No existe CI.
- No hay export de dashboards Kibana.
- No hay scripts completos de instalación, reset, backup y sincronización VPS.
- `scripts/__pycache__/` y archivos `*.pyc` no están excluidos explícitamente.
- Las evidencias JSON deben revisarse antes de versionar para evitar duplicación o crecimiento innecesario.

---

# Roadmap propuesto — Pendiente de aprobación

> Las siguientes fases son una propuesta de orden natural. No deben implementarse hasta recibir aprobación explícita.

## Fase 8 — Cerrar la base reproducible

Objetivo: convertir el LAB actual en una instalación realmente repetible para terceros.

- [ ] Crear una línea base Git limpia y commits por fase.
- [ ] Corregir `.gitignore` para Python, caches y artefactos runtime.
- [ ] Eliminar rutas específicas del equipo local.
- [ ] Encapsular el procesador dentro de Docker.
- [ ] Crear `setup.ps1`, `reset_lab.ps1`, `backup.ps1` y validación automática.
- [ ] Agregar healthchecks y dependencias por estado saludable.
- [ ] Crear migraciones versionadas para PostgreSQL.
- [ ] Lograr el flujo esperado:

```text
git clone
copiar .env.example a .env
docker compose --profile lab up -d
ejecutar demo
```

- [ ] Reemplazar la descarga externa de `example.com` por un servidor HTTP interno que Cowrie pueda resolver correctamente.
- [ ] Crear un smoke test automatizado del LAB.

## Fase 9 — Pipeline n8n real y trazable

Objetivo: recuperar n8n como orquestador efectivo, no solo como workflow importado.

- [ ] Configurar credenciales reproducibles de PostgreSQL.
- [ ] Ejecutar el parser NDJSON desde n8n.
- [ ] Persistir e indexar sin depender del script manual del host.
- [ ] Registrar cada ejecución en `pipeline_runs`.
- [ ] Manejar errores parciales, reintentos y eventos inválidos.
- [ ] Evitar reprocesamiento mediante cursor, offset o checkpoint.
- [ ] Validar el workflow punta a punta con evidencia.
- [ ] Definir si el procesador Python queda como worker del workflow o como herramienta de recuperación.

## Fase 10 — Modelo analítico por sesión y Attack Risk Score

Objetivo: agregar la principal contribución analítica propia.

- [ ] Crear entidad o vista de sesiones correlacionadas.
- [ ] Agrupar eventos por `session_id`.
- [ ] Diseñar reglas versionadas de puntuación.
- [ ] Registrar motivos de cada puntuación.
- [ ] Clasificar sesiones:

```text
0-20:  Bajo
21-50: Medio
51-80: Alto
81+:   Crítico
```

- [ ] Incluir señales como login exitoso, usuarios privilegiados, reconocimiento, descarga, persistencia, reputación del hash y origen cloud.
- [ ] Crear pruebas unitarias para el score.

## Fase 11 — API y aplicación web propia

Objetivo: construir OSCORP ThreatLab como producto propio.

- [ ] Crear backend API, preferentemente FastAPI.
- [ ] Crear frontend/dashboard interactivo.
- [ ] Mostrar resumen general, sesiones, eventos, comandos, descargas y alertas.
- [ ] Crear detalle completo por sesión.
- [ ] Mostrar Attack Risk Score y sus motivos.
- [ ] Permitir marcar sesiones como revisadas.
- [ ] Agregar filtros temporales, IP, país, usuario, evento y criticidad.
- [ ] Permitir exportar datos y reportes.
- [ ] Mantener Kibana como herramienta complementaria.

## Fase 12 — Alertas y MTTD real

Objetivo: reemplazar la estimación teórica por medición real evento-alerta.

- [ ] Completar la tabla `alerts` con:

```text
event_hash
session_id
event_timestamp
processed_timestamp
alert_sent_timestamp
mttd_seconds
alert_channel
alert_status
error_detail
```

- [ ] Integrar Telegram.
- [ ] Registrar alertas exitosas y fallidas.
- [ ] Calcular:

```text
MTTD promedio
MTTD mínimo
MTTD máximo
Percentil 95
Latencia por tipo de evento
Cantidad y porcentaje de alertas fallidas
```

- [ ] Mostrar las métricas en el dashboard propio.

## Fase 13 — Enriquecimiento y mapa geográfico

Objetivo: contextualizar IPs y archivos descargados.

- [ ] Integrar ip-api con cache para evitar consultas repetidas.
- [ ] Guardar país, ciudad, ISP, ASN, latitud y longitud.
- [ ] Integrar VirusTotal para hashes.
- [ ] Guardar resultados, fecha de consulta y errores.
- [ ] Incorporar enriquecimiento al Risk Score.
- [ ] Crear mapa geográfico en Kibana.
- [ ] Crear visualización geográfica equivalente en la aplicación propia.

## Fase 14 — Reportes automáticos

Objetivo: agregar inteligencia operativa periódica.

- [ ] Generar reporte diario y semanal.
- [ ] Incluir:

```text
Total de eventos
IPs y sesiones únicas
Países detectados
Usuarios y contraseñas más probados
Comandos más ejecutados
Archivos y hashes descargados
Hashes maliciosos
Sesiones más críticas
MTTD real
Alertas fallidas
```

- [ ] Exportar al menos HTML/PDF y CSV.
- [ ] Permitir envío por Telegram y descarga desde la aplicación.

## Fase 15 — Dashboards Kibana versionados

Objetivo: dejar una capa analítica complementaria importable.

- [ ] Crear data view para `cowrie-events`.
- [ ] Crear paneles operativos y temporales.
- [ ] Crear visualizaciones de riesgo.
- [ ] Crear mapa geográfico.
- [ ] Exportar dashboards a `kibana/dashboards.ndjson`.
- [ ] Documentar importación automática.

## Fase 16 — Modo REAL/VPS opcional

Objetivo: capturar tráfico real sin convertir la VPS en requisito del sistema.

- [ ] Diseñar despliegue seguro de Cowrie en VPS.
- [ ] Automatizar instalación y actualización.
- [ ] Implementar sincronización o envío continuo de eventos.
- [ ] Evitar depender de que la PC local esté encendida mediante una arquitectura definida.
- [ ] Gestionar secretos y cifrado.
- [ ] Separar datos LAB de datos REAL.
- [ ] Comparar resultados simulados y reales.

## Fase 17 — Calidad, entrega y actualización de tesis

Objetivo: cerrar el proyecto como producto académico reproducible.

- [ ] Agregar tests, CI y controles de calidad.
- [ ] Validar instalación desde una máquina limpia.
- [ ] Crear diagrama final de arquitectura.
- [ ] Crear video demo.
- [ ] Consolidar evidencias y métricas.
- [ ] Revisar seguridad y privacidad de datos.
- [ ] Actualizar el PDF de la tesis con la arquitectura y resultados definitivos.
- [ ] Registrar diferencias entre el sistema original y OSCORP ThreatLab reestructurado.

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
