#!/usr/bin/env bash
# fix_cowrie_json.sh — diagnóstico y corrección definitiva del output JSON de Cowrie
# Ejecutar en la VPS como root o con sudo:
#   bash fix_cowrie_json.sh [/opt/oscorp-cowrie]
set -euo pipefail

REMOTE_DIR="${1:-/opt/oscorp-cowrie}"
CONTAINER=oscorp_vps_cowrie
LOG_PATH_IN_CONTAINER="/cowrie/cowrie-git/var/log/cowrie"

echo "==========================================================="
echo " DIAGNÓSTICO DE COWRIE JSON OUTPUT"
echo "==========================================================="

# ── 1. CWD real del proceso Cowrie ────────────────────────────────────────────
echo ""
echo "[1] CWD del proceso Cowrie dentro del contenedor"
PID=$(docker exec "$CONTAINER" pgrep -f "twistd\|python" 2>/dev/null | head -1 || true)
if [ -n "$PID" ]; then
  CWD=$(docker exec "$CONTAINER" readlink "/proc/$PID/cwd" 2>/dev/null || echo "desconocido")
  echo "    PID=$PID  CWD=$CWD"
else
  echo "    No se encontró proceso Cowrie en el contenedor"
fi

# ── 2. Fuente de jsonlog.py ──────────────────────────────────────────────────
echo ""
echo "[2] Ubicación y lógica de escritura de jsonlog.py"
JSONLOG=$(docker exec "$CONTAINER" find /cowrie -name "jsonlog.py" 2>/dev/null | head -1 || true)
if [ -n "$JSONLOG" ]; then
  echo "    Archivo: $JSONLOG"
  echo "    --- Fragmento relevante (start / logfile) ---"
  docker exec "$CONTAINER" grep -A10 "def start\|logfile\|log_path\|open(" "$JSONLOG" 2>/dev/null || true
else
  echo "    jsonlog.py NO encontrado — buscando jsonfile.py..."
  JSONLOG=$(docker exec "$CONTAINER" find /cowrie -name "jsonfile.py" 2>/dev/null | head -1 || true)
  [ -n "$JSONLOG" ] && echo "    Encontrado: $JSONLOG" || echo "    Ningún plugin JSON encontrado"
fi

# ── 3. Archivos .json dentro del contenedor ───────────────────────────────────
echo ""
echo "[3] Archivos .json dentro del contenedor (excluye node_modules)"
docker exec "$CONTAINER" find /cowrie -name "*.json" 2>/dev/null || true

# ── 4. Descriptores de archivo abiertos por el proceso ───────────────────────
echo ""
echo "[4] Descriptores de archivo abiertos por Cowrie (filtro: log/json)"
if [ -n "$PID" ]; then
  docker exec "$CONTAINER" ls -la "/proc/$PID/fd" 2>/dev/null \
    | grep -E "log|json|cowrie" || echo "    Ninguno que contenga log/json/cowrie"
fi

# ── 5. Cowrie.cfg montado dentro del contenedor ───────────────────────────────
echo ""
echo "[5] cowrie.cfg efectivo dentro del contenedor"
docker exec "$CONTAINER" cat /cowrie/cowrie-git/etc/cowrie.cfg 2>/dev/null \
  || docker exec "$CONTAINER" cat /cowrie/etc/cowrie.cfg 2>/dev/null \
  || echo "    No se encontró cowrie.cfg"

# ── 6. log_path en cowrie.cfg.dist ───────────────────────────────────────────
echo ""
echo "[6] log_path definido en cowrie.cfg.dist"
docker exec "$CONTAINER" grep -E "log_path|data_path" \
  /cowrie/cowrie-git/etc/cowrie.cfg.dist 2>/dev/null || true

echo ""
echo "==========================================================="
echo " APLICANDO FIX"
echo "==========================================================="

# Determinar el log_path real: tomarlo de cfg.dist si existe
LOG_PATH_DIST=$(docker exec "$CONTAINER" \
  grep "^log_path" /cowrie/cowrie-git/etc/cowrie.cfg.dist 2>/dev/null \
  | awk -F= '{print $2}' | tr -d ' ' | head -1 || true)

if [ -n "$LOG_PATH_DIST" ]; then
  # Resolver relativo a CWD si no es absoluto
  if [[ "$LOG_PATH_DIST" != /* ]]; then
    CWD="${CWD:-/cowrie/cowrie-git}"
    LOG_PATH_ABS="$CWD/$LOG_PATH_DIST"
  else
    LOG_PATH_ABS="$LOG_PATH_DIST"
  fi
  echo "[fix] log_path detectado en cfg.dist: $LOG_PATH_DIST → absoluto: $LOG_PATH_ABS"
else
  LOG_PATH_ABS="$LOG_PATH_IN_CONTAINER"
  echo "[fix] log_path no encontrado en cfg.dist; usando default: $LOG_PATH_ABS"
fi

LOGFILE_ABS="$LOG_PATH_ABS/cowrie.json"
echo "[fix] logfile absoluto que se escribirá en cowrie.cfg: $LOGFILE_ABS"

# ── Actualizar cowrie.cfg con ruta absoluta y sección correcta ───────────────
echo ""
echo "[fix] Escribiendo $REMOTE_DIR/etc/cowrie.cfg con logfile absoluto..."
sudo tee "$REMOTE_DIR/etc/cowrie.cfg" >/dev/null <<EOF
[output_jsonlog]
enabled = true
logfile = $LOGFILE_ABS
EOF

echo "[fix] Contenido escrito:"
cat "$REMOTE_DIR/etc/cowrie.cfg"

# ── Ajustar bind mount si log_path_abs difiere del mount actual ──────────────
if [ "$LOG_PATH_ABS" != "$LOG_PATH_IN_CONTAINER" ]; then
  echo ""
  echo "[fix] ATENCIÓN: el path real ($LOG_PATH_ABS) difiere del bind mount actual ($LOG_PATH_IN_CONTAINER)"
  echo "[fix] Actualizando docker-compose.yml para montar $LOG_PATH_ABS..."
  sudo sed -i "s|$LOG_PATH_IN_CONTAINER|$LOG_PATH_ABS|g" "$REMOTE_DIR/docker-compose.yml"
  echo "[fix] docker-compose.yml actualizado:"
  grep "volumes" -A5 "$REMOTE_DIR/docker-compose.yml"
fi

# ── Asegurar permisos del directorio de logs en el host ───────────────────────
HOST_LOG_DIR="$REMOTE_DIR/logs"
echo ""
echo "[fix] Asegurando permisos en $HOST_LOG_DIR..."
sudo mkdir -p "$HOST_LOG_DIR"
sudo chown 1000:1000 "$HOST_LOG_DIR"
sudo chmod 0775 "$HOST_LOG_DIR"
# Eliminar cowrie.json previo vacío para que Cowrie lo cree limpio
[ -f "$HOST_LOG_DIR/cowrie.json" ] && sudo rm -f "$HOST_LOG_DIR/cowrie.json" && echo "[fix] cowrie.json previo eliminado"

# ── Recrear el contenedor ─────────────────────────────────────────────────────
echo ""
echo "[fix] Recreando contenedor con configuración actualizada..."
cd "$REMOTE_DIR"
sudo docker rm -f "$CONTAINER" 2>/dev/null || true
sudo docker compose --env-file .env up -d
echo "[fix] Contenedor iniciado. Esperando 15 s para que Cowrie cargue..."
sleep 15

# ── Verificación final ────────────────────────────────────────────────────────
echo ""
echo "==========================================================="
echo " VERIFICACIÓN"
echo "==========================================================="

echo "[check] Mounts del contenedor:"
docker inspect "$CONTAINER" --format '{{ range .Mounts }}{{ .Type }} {{ .Source }} → {{ .Destination }}{{ "\n" }}{{ end }}'

echo ""
echo "[check] Plugin cargado (buscar 'jsonlog' en logs):"
docker logs "$CONTAINER" 2>&1 | grep -i "jsonlog\|output engine\|error\|Error" | tail -10 || true

echo ""
echo "[check] cowrie.json en host (debe existir y tener líneas tras recibir tráfico):"
ls -lh "$HOST_LOG_DIR/cowrie.json" 2>/dev/null || echo "    No existe aún — esperar primer evento SSH"
wc -l "$HOST_LOG_DIR/cowrie.json" 2>/dev/null || true

echo ""
echo "[check] Descriptores abiertos por Cowrie en el nuevo contenedor:"
NEW_PID=$(docker exec "$CONTAINER" pgrep -f "twistd\|python" 2>/dev/null | head -1 || true)
if [ -n "$NEW_PID" ]; then
  docker exec "$CONTAINER" ls -la "/proc/$NEW_PID/fd" 2>/dev/null \
    | grep -E "log|json|cowrie" \
    || echo "    Ningún descriptor con log/json — revisar si logfile_abs es correcto"
fi

echo ""
echo "Si cowrie.json sigue vacío tras el primer evento SSH:"
echo "  docker exec $CONTAINER cat /proc/$NEW_PID/fd/* 2>/dev/null | grep cowrie"
echo "  docker exec $CONTAINER ls -la $LOG_PATH_ABS/"
