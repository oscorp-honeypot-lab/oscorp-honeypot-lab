param(
    [switch]$NoBuild,
    [switch]$SkipN8nConfig,
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Invoke-Docker {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    & docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker fallo: docker $($Arguments -join ' ')"
    }
}

function Get-DotEnvValue {
    param([string]$Name)

    foreach ($line in Get-Content -LiteralPath ".env") {
        if ($line -match "^\s*$([regex]::Escape($Name))=(.*)$") {
            return $Matches[1].Trim()
        }
    }
    return $null
}

function Set-DotEnvValue {
    param(
        [string]$Name,
        [string]$Value
    )

    $lines = [System.Collections.Generic.List[string]](
        [string[]](Get-Content -LiteralPath ".env")
    )
    $updated = $false
    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -match "^\s*$([regex]::Escape($Name))=") {
            $lines[$index] = "$Name=$Value"
            $updated = $true
            break
        }
    }
    if (-not $updated) {
        $lines.Add("$Name=$Value")
    }
    [System.IO.File]::WriteAllLines(
        (Resolve-Path ".env"),
        $lines,
        [System.Text.UTF8Encoding]::new($false)
    )
}

function New-SecretValue {
    param([int]$Bytes = 32)

    $secretBytes = [byte[]]::new($Bytes)
    $random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $random.GetBytes($secretBytes)
    }
    finally {
        $random.Dispose()
    }
    return [Convert]::ToBase64String($secretBytes).
        TrimEnd("=").
        Replace("+", "-").
        Replace("/", "_")
}

function Get-PersistedN8nEncryptionKey {
    $containerId = (& docker compose ps -aq n8n 2>$null) -join ""
    if ([string]::IsNullOrWhiteSpace($containerId)) {
        return $null
    }

    $temporaryConfig = [System.IO.Path]::GetTempFileName()
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & docker cp "${containerId}:/home/node/.n8n/config" $temporaryConfig 2>$null
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            return $null
        }
        $config = Get-Content -Raw -LiteralPath $temporaryConfig | ConvertFrom-Json
        return [string]$config.encryptionKey
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
        Remove-Item -LiteralPath $temporaryConfig -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "[real-setup] Verificando Docker..."
Invoke-Docker info *> $null

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
    Write-Host "[real-setup] Se creo .env desde .env.example."
}

$encryptionKey = Get-DotEnvValue -Name "N8N_ENCRYPTION_KEY"
$persistedEncryptionKey = Get-PersistedN8nEncryptionKey
if (-not [string]::IsNullOrWhiteSpace($persistedEncryptionKey)) {
    if ($encryptionKey -ne $persistedEncryptionKey) {
        Set-DotEnvValue -Name "N8N_ENCRYPTION_KEY" -Value $persistedEncryptionKey
        $encryptionKey = $persistedEncryptionKey
        Write-Host "[real-setup] Se recupero la clave de cifrado del volumen n8n existente."
    }
}
elseif ([string]::IsNullOrWhiteSpace($encryptionKey)) {
    $encryptionKey = New-SecretValue -Bytes 32
    Set-DotEnvValue -Name "N8N_ENCRYPTION_KEY" -Value $encryptionKey
    Write-Host "[real-setup] Se genero una clave local estable para cifrar credenciales n8n."
}

$adminPassword = Get-DotEnvValue -Name "OSCORP_API_ADMIN_PASSWORD"
if ([string]::IsNullOrWhiteSpace($adminPassword)) {
    $adminPassword = New-SecretValue -Bytes 24
    Set-DotEnvValue -Name "OSCORP_API_ADMIN_PASSWORD" -Value $adminPassword
    Write-Host "[real-setup] Se genero una contrasena local para el administrador."
}

$apiEnvironment = Get-DotEnvValue -Name "OSCORP_API_ENVIRONMENT"
$cookieSecure = Get-DotEnvValue -Name "OSCORP_API_COOKIE_SECURE"
if ($apiEnvironment -match "^(real|production)$" -and $cookieSecure -ne "true") {
    throw "OSCORP_API_ENVIRONMENT=$apiEnvironment requiere OSCORP_API_COOKIE_SECURE=true. Para uso local HTTP, deje OSCORP_API_ENVIRONMENT=lab aunque use el perfil Docker real."
}

Write-Host "[real-setup] Validando Docker Compose perfil real..."
Invoke-Docker compose --profile real config --quiet

if ($ValidateOnly) {
    Write-Host "[real-setup] Validacion local completada sin levantar servicios."
    return
}

$upArguments = @("compose", "--profile", "real", "up", "-d", "--wait")
if (-not $NoBuild) {
    $upArguments += "--build"
}

Write-Host "[real-setup] Levantando stack local REAL..."
Invoke-Docker @upArguments

Write-Host "[real-setup] Inicializando identidad administrativa..."
Invoke-Docker compose exec -T backend python -m app.infrastructure.bootstrap

if (-not $SkipN8nConfig) {
    & "$PSScriptRoot\configure_n8n_assets.ps1"
}

Write-Host "[real-setup] Stack REAL listo."
Write-Host "[real-setup] App web: http://localhost:5173/dashboard"
Write-Host "[real-setup] Para sincronizar eventos reales: .\scripts\sync_vps_logs.ps1 -RunPipeline"
