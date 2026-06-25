$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$marker = "phase12-$([guid]::NewGuid())"
$invalidLine = "{`"eventid`":invalid,`"marker`":`"$marker`"}"
& docker compose stop cowrie
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo detener Cowrie."
}
try {
    Add-Content -LiteralPath "cowrie\logs\cowrie.json" `
        -Value $invalidLine `
        -Encoding UTF8
}
finally {
    & docker compose up -d --wait cowrie
    if ($LASTEXITCODE -ne 0) {
        throw "Cowrie no volvió a estado saludable."
    }
}

Write-Host "[partial-errors] Procesando línea inválida..."
$output = & "$PSScriptRoot\run_n8n_pipeline.ps1"
$output | Write-Output

$runIdMatch = @($output | Select-String '^run_id=(\d+)$')[-1]
$errorsMatch = @($output | Select-String '^errors_count=(\d+)$')[-1]
if (-not $runIdMatch -or -not $errorsMatch) {
    throw "No se obtuvieron métricas del pipeline."
}
$runId = [int]$runIdMatch.Matches[0].Groups[1].Value
$errors = [int]$errorsMatch.Matches[0].Groups[1].Value
if ($errors -ne 1) {
    throw "Se esperaba un error parcial y se obtuvieron $errors."
}

$stored = (& docker compose exec -T postgres psql -U oscorp -d oscorp -At -F "|" -c @"
SELECT
    pr.status,
    pr.errors_count,
    COUNT(pe.id),
    MIN(pe.error_code)
FROM pipeline_runs pr
LEFT JOIN pipeline_event_errors pe ON pe.run_id = pr.id
WHERE pr.id = $runId
GROUP BY pr.status, pr.errors_count;
"@).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo consultar la cuarentena."
}
if ($stored -ne "completed_with_errors|1|1|invalid_json") {
    throw "Estado parcial inesperado: $stored"
}

Write-Host "[partial-errors] Cuarentena validada: $stored"

$next = & "$PSScriptRoot\run_n8n_pipeline.ps1"
$next | Write-Output
$nextRead = @($next | Select-String '^events_read=(\d+)$')[-1]
$nextErrors = @($next | Select-String '^errors_count=(\d+)$')[-1]
if (
    [int]$nextRead.Matches[0].Groups[1].Value -ne 0 -or
    [int]$nextErrors.Matches[0].Groups[1].Value -ne 0
) {
    throw "La línea en cuarentena volvió a bloquear o reprocesarse."
}
