#!/usr/bin/env bash
set -euo pipefail

echo "[full] Iniciando secuencia completa: fuerza bruta, reconocimiento y descarga simulada."

bash /app/scenarios/brute_force.sh
sleep 2

bash /app/scenarios/recon.sh
sleep 2

bash /app/scenarios/malware_download.sh

echo "[full] Secuencia completa finalizada."
