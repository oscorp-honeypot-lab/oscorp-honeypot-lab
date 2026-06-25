$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Get-DotEnvValue {
    param(
        [string]$Name,
        [string]$Default = ""
    )

    foreach ($line in Get-Content -LiteralPath ".env") {
        if ($line -match "^\s*$([regex]::Escape($Name))=(.*)$") {
            return $Matches[1].Trim()
        }
    }
    return $Default
}

function Invoke-Docker {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    & docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker falló: docker $($Arguments -join ' ')"
    }
}

if (-not (Test-Path -LiteralPath ".env")) {
    throw "Falta .env. Ejecute scripts\setup.ps1 primero."
}

$postgresDatabase = Get-DotEnvValue -Name "POSTGRES_DB" -Default "oscorp"
$postgresUser = Get-DotEnvValue -Name "POSTGRES_USER" -Default "oscorp"
$postgresPassword = Get-DotEnvValue -Name "POSTGRES_PASSWORD"
$elasticsearchUsername = Get-DotEnvValue -Name "ELASTICSEARCH_USERNAME"
$elasticsearchPassword = Get-DotEnvValue -Name "ELASTICSEARCH_PASSWORD"

if ([string]::IsNullOrWhiteSpace($postgresPassword)) {
    throw "POSTGRES_PASSWORD no puede estar vacío para configurar n8n."
}

$credentials = @(
    [ordered]@{
        id = "oscorp-postgres"
        name = "OSCORP Postgres"
        type = "postgres"
        data = [ordered]@{
            host = "postgres"
            database = $postgresDatabase
            user = $postgresUser
            password = $postgresPassword
            maxConnections = 10
            allowUnauthorizedCerts = $false
            ssl = "disable"
            port = 5432
            sshTunnel = $false
        }
    },
    [ordered]@{
        id = "oscorp-elasticsearch"
        name = "OSCORP Elasticsearch"
        type = "elasticsearchApi"
        data = [ordered]@{
            username = $elasticsearchUsername
            password = $elasticsearchPassword
            baseUrl = "http://elasticsearch:9200"
            ignoreSSLIssues = $false
        }
    }
)

$credentialPath = Join-Path $ProjectRoot "n8n\credentials\oscorp-credentials.generated.json"
$credentialJson = ConvertTo-Json -InputObject $credentials -Depth 8

try {
    [System.IO.File]::WriteAllText(
        $credentialPath,
        $credentialJson,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "[n8n] Importando credenciales OSCORP cifradas..."
    Invoke-Docker compose exec -T n8n n8n import:credentials --input=/files/credentials/oscorp-credentials.generated.json

    Write-Host "[n8n] Sincronizando workflow versionado..."
    Invoke-Docker compose exec -T n8n n8n import:workflow --input=/files/workflows/oscorp-workflow.json
}
finally {
    if (Test-Path -LiteralPath $credentialPath) {
        Remove-Item -LiteralPath $credentialPath -Force
    }
}

$workflowList = & docker compose exec -T n8n n8n list:workflow 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo consultar los workflows de n8n."
}
if (($workflowList -join "`n") -notmatch "oscorp-cowrie-ndjson-pipeline") {
    throw "El workflow OSCORP no quedó importado."
}

Write-Host "[n8n] Credenciales y workflow sincronizados."
