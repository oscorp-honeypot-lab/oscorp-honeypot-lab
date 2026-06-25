$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$requestId = [guid]::NewGuid().ToString()
$sessionId = "phase12-$([guid]::NewGuid().ToString('N').Substring(0, 12))"
$event = @{
    eventid = "cowrie.test.recovery"
    session = $sessionId
    sensor = "phase12-validation"
    timestamp = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json -Compress

& docker compose stop cowrie
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo detener Cowrie."
}
try {
    Add-Content -LiteralPath "cowrie\logs\cowrie.json" -Value $event -Encoding UTF8
}
finally {
    & docker compose up -d --wait cowrie
    if ($LASTEXITCODE -ne 0) {
        throw "Cowrie no volvió a estado saludable."
    }
}

$payload = @{
    contract_version = "1.0"
    request_id = $requestId
    triggered_by = "n8n_manual"
    mode = "incremental"
    source = "cowrie_ndjson"
} | ConvertTo-Json -Compress
$payloadBase64 = [Convert]::ToBase64String(
    [Text.Encoding]::UTF8.GetBytes($payload)
)

function Invoke-Worker {
    $command = "echo '$payloadBase64' | base64 -d | curl -fsS " +
        "-H 'Content-Type: application/json' --data-binary @- " +
        "http://pipeline-worker:8080/runs"
    $response = & docker compose exec -T attacker-sim sh -c $command
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo invocar pipeline-worker."
    }
    return ($response -join "`n") | ConvertFrom-Json
}

Write-Host "[recovery] Forzando indisponibilidad de Elasticsearch..."
& docker compose stop elasticsearch
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo detener Elasticsearch."
}
try {
    $failed = Invoke-Worker
}
finally {
    & docker compose up -d --wait elasticsearch
    if ($LASTEXITCODE -ne 0) {
        throw "Elasticsearch no volvió a estado saludable."
    }
}

if ($failed.status -ne "failed" -or $failed.error_code -ne "elasticsearch_failed") {
    throw "Fallo controlado inesperado: $($failed | ConvertTo-Json -Compress)"
}

Write-Host "[recovery] Reintentando la misma solicitud..."
$recovered = Invoke-Worker
if ($recovered.status -ne "completed" -or $recovered.run_id -ne $failed.run_id) {
    throw "La recuperación no reutilizó el pipeline_run."
}

$stored = (& docker compose exec -T postgres psql -U oscorp -d oscorp -At -F "|" -c @"
SELECT status, attempt_count, events_read, events_inserted, events_indexed, errors_count
FROM pipeline_runs
WHERE request_id = '$requestId';
"@).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo verificar la recuperación."
}
$parts = $stored -split "\|"
if (
    $parts[0] -ne "completed" -or
    $parts[1] -ne "2" -or
    [int]$parts[2] -lt 1 -or
    $parts[3] -ne "0" -or
    $parts[4] -ne $parts[2] -or
    $parts[5] -ne "0"
) {
    throw "Resultado de recuperación inesperado: $stored"
}

Write-Host "[recovery] Recuperación validada: $stored"
