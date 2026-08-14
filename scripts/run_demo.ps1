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

$CowrieLogPath = "/cowrie/cowrie-git/var/log/cowrie/cowrie.json"
$CowriePython = "/cowrie/cowrie-env/bin/python"

function Get-CowrieContainerLogLineCount {
    # Se consulta directamente al contenedor (docker exec) en vez del bind mount del host:
    # en Docker Desktop con backend WSL2, las escrituras por append del contenedor hacia un
    # bind mount que vive en NTFS (C:\...) tardan en propagarse a la vista del host por el
    # passthrough Windows<->WSL2. Leer el archivo desde adentro del contenedor evita ese lag.
    # La imagen de cowrie no trae coreutils (ni wc, ni tail, ni sh) — se usa el python del venv.
    $script = "print(sum(1 for _ in open('$CowrieLogPath', 'rb')))"
    $result = & docker compose exec -T cowrie $CowriePython -c $script
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo consultar el log de Cowrie dentro del contenedor."
    }
    return [int]$result.Trim()
}

function Get-CowrieContainerLogTail {
    param([int]$Skip)
    $script = "import sys; f = open('$CowrieLogPath', 'rb'); lines = f.readlines(); sys.stdout.buffer.write(b''.join(lines[${Skip}:]))"
    $raw = & docker compose exec -T cowrie $CowriePython -c $script
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo leer el log de Cowrie dentro del contenedor."
    }
    return $raw
}

function Reset-CowrieJsonLogObserver {
    # El output observer de Twisted que escribe cowrie.json (cowrie/output/jsonlog.py) puede
    # quedar deshabilitado en silencio tras un fallo de escritura transitorio en el bind mount
    # (típico del passthrough NTFS<->WSL2 de Docker Desktop en Windows). El honeypot sigue
    # funcionando con normalidad (SSH, log de stdout) pero deja de escribir eventos en
    # cowrie.json para siempre hasta que se reinicia el proceso. Reiniciar el contenedor antes
    # de la campaña re-inicializa el observer; el archivo no se trunca (honeypot.logtype=rotating).
    Invoke-Docker compose restart cowrie
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        $health = (& docker compose ps cowrie --format json | ConvertFrom-Json).Health
        if ($health -eq "healthy") {
            return
        }
        Start-Sleep -Seconds 1
    }
    throw "El contenedor cowrie no volvió a healthy tras el reinicio."
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

Write-Host "[demo] Reiniciando cowrie para garantizar un observer de log limpio..."
Reset-CowrieJsonLogObserver
$beforeLogLines = Get-CowrieContainerLogLineCount

Write-Host "[demo] Ejecutando ataque completo..."
Invoke-Docker compose --profile lab run --rm attacker-sim ./run_scenario.sh full

$maxAttempts = 30
$afterAttackLogLines = $beforeLogLines
for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
    $afterAttackLogLines = Get-CowrieContainerLogLineCount
    if ($afterAttackLogLines -gt $beforeLogLines) {
        break
    }
    Start-Sleep -Seconds 1
}
if ($afterAttackLogLines -le $beforeLogLines) {
    throw "Cowrie no generó eventos nuevos."
}

$newEvents = Get-CowrieContainerLogTail -Skip $beforeLogLines |
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
