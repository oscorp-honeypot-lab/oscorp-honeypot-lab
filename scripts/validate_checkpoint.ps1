$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Get-Metric {
    param(
        [string[]]$Output,
        [string]$Name
    )

    $match = @(
        $Output |
            Select-String -Pattern "^$([regex]::Escape($Name))=(\d+)$"
    )[-1]
    if (-not $match) {
        throw "No se encontró la métrica $Name."
    }
    return [long]$match.Matches[0].Groups[1].Value
}

function Invoke-Pipeline {
    $output = & "$PSScriptRoot\run_n8n_pipeline.ps1"
    $output | ForEach-Object { Write-Host $_ }
    return ,$output
}

Write-Host "[checkpoint] Estableciendo checkpoint..."
$initial = Invoke-Pipeline

Write-Host "[checkpoint] Verificando ejecución sin novedades..."
$second = Invoke-Pipeline
if ((Get-Metric $second "events_read") -ne 0) {
    throw "La segunda ejecución volvió a leer eventos ya confirmados."
}
if (
    (Get-Metric $second "source_offset_start") -ne
    (Get-Metric $second "source_offset_end")
) {
    throw "El offset avanzó sin eventos nuevos."
}

Write-Host "[checkpoint] Reiniciando worker..."
& docker compose restart pipeline-worker
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo reiniciar pipeline-worker."
}
& docker compose up -d --wait pipeline-worker
if ($LASTEXITCODE -ne 0) {
    throw "pipeline-worker no volvió a estado saludable."
}

$afterRestart = Invoke-Pipeline
if ((Get-Metric $afterRestart "events_read") -ne 0) {
    throw "El reinicio provocó reprocesamiento."
}

$checkpoint = (& docker compose exec -T postgres psql -U oscorp -d oscorp -At -F "|" -c @"
SELECT byte_offset, line_number, last_run_id
FROM pipeline_checkpoints
WHERE source_key = 'cowrie_ndjson';
"@).Trim()
if ($LASTEXITCODE -ne 0 -or -not $checkpoint) {
    throw "No se pudo verificar el checkpoint persistente."
}

Write-Host "[checkpoint] Checkpoint persistente validado: $checkpoint"
