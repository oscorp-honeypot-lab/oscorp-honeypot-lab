$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$requestId = [guid]::NewGuid().ToString()
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

Write-Host "[traceability] Enviando solicitud correlacionada..."
$first = Invoke-Worker
$second = Invoke-Worker

if ($first.run_id -ne $second.run_id) {
    throw "El reintento creó una ejecución duplicada."
}

$stored = (& docker compose exec -T postgres psql -U oscorp -d oscorp -At -F "|" -c @"
SELECT COUNT(*), MIN(id), MIN(triggered_by), MIN(status)
FROM pipeline_runs
WHERE request_id = '$requestId';
"@).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo consultar la trazabilidad."
}

$parts = $stored -split "\|"
if ($parts[0] -ne "1" -or [int]$parts[1] -ne [int]$first.run_id) {
    throw "La trazabilidad por request_id es inconsistente: $stored"
}

Write-Host "[traceability] Reintento idempotente validado: $stored"
