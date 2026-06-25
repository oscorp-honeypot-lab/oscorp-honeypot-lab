$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Services = @(
    "postgres",
    "elasticsearch",
    "kibana",
    "n8n",
    "pipeline-worker",
    "cowrie",
    "payload-server",
    "attacker-sim"
)

function Assert-LastExitCode {
    param([string]$Message)
    if ($LASTEXITCODE -ne 0) {
        throw $Message
    }
}

Write-Host "[validate] Verificando contenedores..."
foreach ($service in $Services) {
    $containerId = (& docker compose --profile lab ps -q $service).Trim()
    Assert-LastExitCode "No se pudo consultar el servicio $service."
    if (-not $containerId) {
        throw "El servicio $service no está creado."
    }

    $running = (& docker inspect --format "{{.State.Running}}" $containerId).Trim()
    Assert-LastExitCode "No se pudo inspeccionar el servicio $service."
    if ($running -ne "true") {
        throw "El servicio $service no está en ejecución."
    }

    $health = (& docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}" $containerId).Trim()
    Assert-LastExitCode "No se pudo consultar el healthcheck de $service."
    if ($health -notin @("healthy", "none")) {
        throw "El servicio $service tiene estado de salud: $health."
    }
}

Write-Host "[validate] Verificando PostgreSQL..."
& docker compose exec -T postgres pg_isready -U oscorp -d oscorp | Out-Null
Assert-LastExitCode "PostgreSQL no acepta conexiones."

$migration = (& docker compose exec -T postgres psql -U oscorp -d oscorp -Atc "SELECT version_num FROM alembic_version;").Trim()
Assert-LastExitCode "No se pudo consultar la migración Alembic."
if ($migration -ne "0004_correlated_sessions") {
    throw "Versión de migración inesperada: $migration"
}

Write-Host "[validate] Verificando Elasticsearch..."
$esHealth = Invoke-RestMethod -Uri "http://localhost:9200/_cluster/health" -TimeoutSec 15
if ($esHealth.status -notin @("yellow", "green")) {
    throw "Elasticsearch no está operativo: $($esHealth.status)"
}

Write-Host "[validate] Verificando Kibana..."
$kibana = Invoke-RestMethod -Uri "http://localhost:5601/api/status" -TimeoutSec 20
if ($kibana.status.overall.level -ne "available") {
    throw "Kibana no está disponible."
}

Write-Host "[validate] Verificando n8n..."
$n8n = Invoke-RestMethod -Uri "http://localhost:5678/healthz" -TimeoutSec 15
if ($n8n.status -ne "ok") {
    throw "n8n no está saludable."
}

Write-Host "[validate] Verificando pipeline-worker..."
$workerHealth = & docker compose exec -T n8n wget -qO- http://pipeline-worker:8080/health
Assert-LastExitCode "pipeline-worker no es accesible desde n8n."
$worker = ($workerHealth -join "`n") | ConvertFrom-Json
if ($worker.status -ne "ok" -or $worker.contract_version -ne "1.0") {
    throw "pipeline-worker no está saludable."
}

Write-Host "[validate] Verificando pruebas Python..."
& docker compose exec -T pipeline-worker python -m unittest discover -s /app/tests -v
Assert-LastExitCode "Las pruebas Python no fueron superadas."

Write-Host "[validate] Verificando payload interno..."
$payload = & docker compose exec -T attacker-sim curl -fsS http://payload-server:8080/mirai.sh
Assert-LastExitCode "El payload-server no es accesible desde attacker-sim."
$payloadText = $payload -join "`n"
if ($payloadText -notmatch "OSCORP harmless simulated payload") {
    throw "El payload interno no coincide con el contenido esperado."
}

Write-Host "[validate] LAB válido."
