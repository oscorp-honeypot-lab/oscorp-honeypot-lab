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

Write-Host "[n8n-contract] Validando artefactos versionados..."
$workflow = Get-Content -Raw -Encoding UTF8 "n8n\workflows\oscorp-workflow.json" |
    ConvertFrom-Json
$requestSchema = Get-Content -Raw -Encoding UTF8 "pipeline\contracts\run-request.schema.json" |
    ConvertFrom-Json
$resultSchema = Get-Content -Raw -Encoding UTF8 "pipeline\contracts\run-result.schema.json" |
    ConvertFrom-Json

if ($workflow.active) {
    throw "El workflow debe permanecer inactivo para ejecución manual controlada."
}
if ($requestSchema.properties.contract_version.const -ne "1.0") {
    throw "Versión inesperada del contrato de solicitud."
}
if ($resultSchema.properties.contract_version.const -ne "1.0") {
    throw "Versión inesperada del contrato de resultado."
}

$workflowText = Get-Content -Raw -Encoding UTF8 "n8n\workflows\oscorp-workflow.json"
$forbiddenPatterns = @(
    "REPLACE_WITH",
    "readBinaryFile",
    "Parse NDJSON",
    "INSERT INTO eventos",
    "/_cluster/health",
    "oscorp123",
    "admin123"
)
foreach ($pattern in $forbiddenPatterns) {
    if ($workflowText.Contains($pattern)) {
        throw "El workflow contiene el patrón prohibido: $pattern"
    }
}

if (Test-Path -LiteralPath "n8n\credentials\oscorp-credentials.generated.json") {
    throw "Quedó un archivo temporal de credenciales en el workspace."
}

Write-Host "[n8n-contract] Sincronizando credenciales y workflow..."
& "$PSScriptRoot\configure_n8n_assets.ps1"

$temporaryExport = [System.IO.Path]::GetTempFileName()
try {
    Invoke-Docker compose exec -T n8n n8n export:credentials --all --output=/tmp/oscorp-credentials-validation.json
    Invoke-Docker cp oscorp_n8n:/tmp/oscorp-credentials-validation.json $temporaryExport
    $exportedCredentials = Get-Content -Raw -LiteralPath $temporaryExport |
        ConvertFrom-Json

    $expectedCredentials = @(
        "oscorp-postgres",
        "oscorp-elasticsearch"
    )
    foreach ($credentialId in $expectedCredentials) {
        $credential = $exportedCredentials |
            Where-Object { $_.id -eq $credentialId } |
            Select-Object -First 1
        if (-not $credential) {
            throw "Falta la credencial n8n: $credentialId"
        }
        if ($credential.data -isnot [string]) {
            throw "La credencial $credentialId no fue exportada cifrada."
        }
    }
}
finally {
    Remove-Item -LiteralPath $temporaryExport -Force -ErrorAction SilentlyContinue
    & docker compose exec -T n8n rm -f /tmp/oscorp-credentials-validation.json 2>$null
}

Write-Host "[n8n-contract] Verificando acceso interno al worker..."
$workerHealth = & docker compose exec -T n8n wget -qO- http://pipeline-worker:8080/health
if ($LASTEXITCODE -ne 0) {
    throw "n8n no puede acceder al pipeline-worker."
}
$worker = ($workerHealth -join "`n") | ConvertFrom-Json
if ($worker.status -ne "ok" -or $worker.contract_version -ne "1.0") {
    throw "Respuesta de salud inválida del pipeline-worker."
}

$executionOutput = & "$PSScriptRoot\run_n8n_pipeline.ps1"
$executionText = $executionOutput -join "`n"
if ($executionText -notmatch 'run_id=\d+') {
    throw "El workflow no confirmó pipeline_runs."
}
if ($executionText -notmatch 'events_read=\d+') {
    throw "El workflow no devolvió métricas del pipeline."
}

Write-Host "[n8n-contract] Contrato, worker y orquestación validados."
