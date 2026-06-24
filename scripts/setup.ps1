param(
    [switch]$NoBuild
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

Write-Host "[setup] Verificando Docker..."
Invoke-Docker info *> $null

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
    Write-Host "[setup] Se creó .env desde .env.example."
}

Write-Host "[setup] Validando Docker Compose..."
Invoke-Docker compose --profile lab config --quiet

$upArguments = @("compose", "--profile", "lab", "up", "-d", "--wait")
if (-not $NoBuild) {
    $upArguments += "--build"
}

Write-Host "[setup] Levantando el perfil LAB..."
Invoke-Docker @upArguments

$workflowList = & docker compose exec -T n8n n8n list:workflow 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo consultar los workflows de n8n."
}
$workflowText = $workflowList -join "`n"

if ($workflowText -notmatch "oscorp-cowrie-ndjson-pipeline") {
    Write-Host "[setup] Importando workflow OSCORP en n8n..."
    Invoke-Docker compose exec -T n8n n8n import:workflow --input=/files/workflows/oscorp-workflow.json
}

Write-Host "[setup] Entorno LAB listo."
