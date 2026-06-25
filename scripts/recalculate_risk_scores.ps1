$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

& docker compose exec -T pipeline-worker python /app/recalculate_risk_scores.py
if ($LASTEXITCODE -ne 0) {
    throw "No se pudieron recalcular los Attack Risk Scores."
}
