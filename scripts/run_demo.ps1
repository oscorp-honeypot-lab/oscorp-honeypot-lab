param(
    [switch]$SkipValidation
)

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

function Get-PostgresEventCount {
    $value = (& docker compose exec -T postgres psql -U oscorp -d oscorp -Atc "SELECT COUNT(*) FROM eventos;").Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo consultar PostgreSQL."
    }
    return [int]$value
}

function Get-ElasticsearchEventCount {
    for ($attempt = 1; $attempt -le 10; $attempt++) {
        try {
            $response = Invoke-RestMethod -Uri "http://localhost:9200/cowrie-events/_count" -TimeoutSec 15
            $count = [int]$response.count
        }
        catch {
            $statusCode = if ($_.Exception.Response.StatusCode) {
                [int]$_.Exception.Response.StatusCode
            }
            if ($statusCode -ne 404) {
                throw
            }
            $count = 0
        }
        if ($count -eq (Get-PostgresEventCount)) {
            return $count
        }
        Start-Sleep -Seconds 1
    }
    return $count
}

function Get-PipelineMetric {
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

if (-not $SkipValidation) {
    & "$PSScriptRoot\validate_lab.ps1"
}

Write-Host "[demo] Sincronizando checkpoint incremental..."
$checkpointOutput = & "$PSScriptRoot\run_n8n_pipeline.ps1"
$checkpointOutput | Write-Output

$beforePostgres = Get-PostgresEventCount
$beforeElasticsearch = Get-ElasticsearchEventCount
$beforeLogLines = (Get-Content -LiteralPath "cowrie\logs\cowrie.json").Count

Write-Host "[demo] Ejecutando ataque completo..."
Invoke-Docker compose --profile lab run --rm attacker-sim ./run_scenario.sh full

$afterAttackLogLines = $beforeLogLines
for ($attempt = 1; $attempt -le 15; $attempt++) {
    $afterAttackLogLines = (Get-Content -LiteralPath "cowrie\logs\cowrie.json").Count
    if ($afterAttackLogLines -gt $beforeLogLines) {
        break
    }
    Start-Sleep -Seconds 1
}
if ($afterAttackLogLines -le $beforeLogLines) {
    throw "Cowrie no generó eventos nuevos."
}

$newEvents = Get-Content -LiteralPath "cowrie\logs\cowrie.json" |
    Select-Object -Skip $beforeLogLines |
    ForEach-Object { $_ | ConvertFrom-Json }

$requiredEventIds = @(
    "cowrie.login.failed",
    "cowrie.login.success",
    "cowrie.command.input",
    "cowrie.session.file_download"
)
foreach ($eventId in $requiredEventIds) {
    if ($eventId -notin $newEvents.eventid) {
        throw "La campaña no generó el evento requerido: $eventId"
    }
}

if (-not ($newEvents.url -match "^http://payload-server:8080/")) {
    throw "La campaña no utilizó el payload-server interno."
}

Write-Host "[demo] Ejecutando pipeline orquestado por n8n..."
$pipelineOutput = & "$PSScriptRoot\run_n8n_pipeline.ps1"
$pipelineOutput | Write-Output
if ((Get-PipelineMetric $pipelineOutput "events_read") -le 0) {
    throw "El pipeline incremental no leyó los eventos nuevos."
}

$afterPostgres = Get-PostgresEventCount
$afterElasticsearch = Get-ElasticsearchEventCount
if ($afterPostgres -le $beforePostgres) {
    throw "PostgreSQL no recibió eventos nuevos."
}
if ($afterElasticsearch -le $beforeElasticsearch) {
    throw "Elasticsearch no recibió eventos nuevos."
}
if ($afterPostgres -ne $afterElasticsearch) {
    throw "PostgreSQL y Elasticsearch tienen conteos distintos."
}

Write-Host "[demo] Verificando idempotencia..."
$idempotentOutput = & "$PSScriptRoot\run_n8n_pipeline.ps1"
$idempotentOutput | Write-Output
if ((Get-PipelineMetric $idempotentOutput "events_read") -ne 0) {
    throw "La segunda ejecución releyó eventos ya confirmados."
}
if (
    (Get-PipelineMetric $idempotentOutput "source_offset_start") -ne
    (Get-PipelineMetric $idempotentOutput "source_offset_end")
) {
    throw "La segunda ejecución avanzó el offset sin eventos nuevos."
}
$idempotentPostgres = Get-PostgresEventCount
$idempotentElasticsearch = Get-ElasticsearchEventCount
if ($idempotentPostgres -ne $afterPostgres) {
    throw "La segunda ejecución duplicó eventos en PostgreSQL."
}
if ($idempotentElasticsearch -ne $afterElasticsearch) {
    throw "La segunda ejecución alteró el conteo de Elasticsearch."
}

Write-Host "[demo] Flujo completo validado."
Write-Host "[demo] Eventos nuevos en PostgreSQL: $($afterPostgres - $beforePostgres)"
Write-Host "[demo] Total acumulado: $afterPostgres"
