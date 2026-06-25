$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Invoke-Docker {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    & docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker falló: docker $($Arguments -join ' ')"
    }
}

Write-Host "[n8n-pipeline] Ejecutando workflow OSCORP..."
Invoke-Docker compose stop n8n
try {
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $executionOutput = & docker compose --profile lab run --rm --no-deps n8n execute --id=oscorp-cowrie-ndjson-pipeline --rawOutput
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    if ($exitCode -ne 0) {
        $executionOutput | Write-Output
        throw "El workflow n8n finalizó con código $exitCode."
    }
}
finally {
    Invoke-Docker compose --profile lab up -d --wait n8n
}

$executionText = $executionOutput -join "`n"
if ($executionText -notmatch '"status":\s*"success"') {
    throw "El workflow n8n no informó estado success."
}
if ($executionText -notmatch '"run_id":\s*\d+') {
    throw "El workflow n8n no devolvió un pipeline_run."
}
$runId = @([regex]::Matches($executionText, '"run_id":\s*(\d+)'))[-1].Groups[1].Value
$eventsRead = @([regex]::Matches($executionText, '"events_read":\s*(\d+)'))[-1].Groups[1].Value
$eventsInserted = @([regex]::Matches($executionText, '"events_inserted":\s*(\d+)'))[-1].Groups[1].Value
$eventsIndexed = @([regex]::Matches($executionText, '"events_indexed":\s*(\d+)'))[-1].Groups[1].Value
$errorsCount = @([regex]::Matches($executionText, '"errors_count":\s*(\d+)'))[-1].Groups[1].Value
$offsetStart = @([regex]::Matches($executionText, '"source_offset_start":\s*(\d+)'))[-1].Groups[1].Value
$offsetEnd = @([regex]::Matches($executionText, '"source_offset_end":\s*(\d+)'))[-1].Groups[1].Value

Write-Output "run_id=$runId"
Write-Output "events_read=$eventsRead"
Write-Output "events_inserted=$eventsInserted"
Write-Output "events_indexed=$eventsIndexed"
Write-Output "errors_count=$errorsCount"
Write-Output "source_offset_start=$offsetStart"
Write-Output "source_offset_end=$offsetEnd"
Write-Host "[n8n-pipeline] Workflow completado."
