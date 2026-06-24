#!/usr/bin/env bash
set -euo pipefail

SCENARIO="${1:-}"

export TARGET_HOST="${TARGET_HOST:-cowrie}"
export TARGET_PORT="${TARGET_PORT:-2222}"
export TARGET_USER="${TARGET_USER:-root}"
export TARGET_PASSWORD="${TARGET_PASSWORD:-admin}"
export PASS_FILE="${PASS_FILE:-/app/passwords.txt}"

usage() {
  cat <<'EOF'
Uso:
  ./run_scenario.sh brute-force
  ./run_scenario.sh recon
  ./run_scenario.sh malware-download
  ./run_scenario.sh full

Variables opcionales:
  TARGET_HOST       Host destino dentro de Docker. Default: cowrie
  TARGET_PORT       Puerto SSH de Cowrie. Default: 2222
  TARGET_USER       Usuario SSH simulado. Default: root
  TARGET_PASSWORD   Password para escenarios post-login. Default: admin
  PASS_FILE         Wordlist para fuerza bruta. Default: /app/passwords.txt
EOF
}

if [[ -z "$SCENARIO" || "$SCENARIO" == "-h" || "$SCENARIO" == "--help" ]]; then
  usage
  exit 0
fi

wait_for_cowrie() {
  echo "[attacker-sim] Verificando conectividad con ${TARGET_HOST}:${TARGET_PORT}..."
  for attempt in $(seq 1 20); do
    if nc -z -w 2 "$TARGET_HOST" "$TARGET_PORT"; then
      echo "[attacker-sim] Cowrie disponible."
      return 0
    fi
    echo "[attacker-sim] Esperando Cowrie (${attempt}/20)..."
    sleep 2
  done

  echo "[attacker-sim] ERROR: no se pudo conectar con ${TARGET_HOST}:${TARGET_PORT}." >&2
  exit 1
}

run_script() {
  local script="$1"
  if [[ ! -f "$script" ]]; then
    echo "[attacker-sim] ERROR: no existe el escenario ${script}." >&2
    exit 1
  fi

  bash "$script"
}

wait_for_cowrie

case "$SCENARIO" in
  brute-force|bruteforce|brute_force)
    run_script "/app/scenarios/brute_force.sh"
    ;;
  recon|reconnaissance)
    run_script "/app/scenarios/recon.sh"
    ;;
  malware-download|malware_download|download)
    run_script "/app/scenarios/malware_download.sh"
    ;;
  full|full-attack|full_attack)
    run_script "/app/scenarios/full_attack.sh"
    ;;
  *)
    echo "[attacker-sim] ERROR: escenario desconocido: ${SCENARIO}" >&2
    usage
    exit 1
    ;;
esac
