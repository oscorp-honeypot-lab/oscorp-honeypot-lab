#!/usr/bin/env bash
set -euo pipefail

TARGET_HOST="${TARGET_HOST:-cowrie}"
TARGET_PORT="${TARGET_PORT:-2222}"
TARGET_USER="${TARGET_USER:-root}"
TARGET_PASSWORD="${TARGET_PASSWORD:-admin}"

SSH_OPTS=(
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
  -o LogLevel=ERROR
  -o ConnectTimeout=8
)

COMMANDS=(
  "whoami"
  "id"
  "uname -a"
  "pwd"
  "ls -la"
  "cat /etc/passwd"
  "ps aux"
  "netstat -tunap"
)

echo "[recon] Ejecutando reconocimiento post-login contra ${TARGET_HOST}:${TARGET_PORT}."

for command in "${COMMANDS[@]}"; do
  echo "[recon] CMD: ${command}"
  sshpass -p "$TARGET_PASSWORD" ssh "${SSH_OPTS[@]}" -p "$TARGET_PORT" "${TARGET_USER}@${TARGET_HOST}" "$command" || true
  sleep 1
done

echo "[recon] Finalizado. Cowrie debería registrar eventos cowrie.command.input."
