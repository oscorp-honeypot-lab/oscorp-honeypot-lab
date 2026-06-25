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

Write-Host "[setup] Verificando Docker..."
Invoke-Docker info *> $null

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
    Write-Host "[setup] Se creó .env desde .env.example."
}

$encryptionKey = Get-DotEnvValue -Name "N8N_ENCRYPTION_KEY"
$persistedEncryptionKey = Get-PersistedN8nEncryptionKey
if (-not [string]::IsNullOrWhiteSpace($persistedEncryptionKey)) {
    if ($encryptionKey -ne $persistedEncryptionKey) {
        Set-DotEnvValue -Name "N8N_ENCRYPTION_KEY" -Value $persistedEncryptionKey
        $encryptionKey = $persistedEncryptionKey
        Write-Host "[setup] Se recuperó la clave de cifrado del volumen n8n existente."
    }
}
elseif ([string]::IsNullOrWhiteSpace($encryptionKey)) {
    $keyBytes = [byte[]]::new(32)
    $random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $random.GetBytes($keyBytes)
    }
    finally {
        $random.Dispose()
    }
    $encryptionKey = ([BitConverter]::ToString($keyBytes) -replace "-", "").ToLowerInvariant()
    Set-DotEnvValue -Name "N8N_ENCRYPTION_KEY" -Value $encryptionKey
    Write-Host "[setup] Se generó una clave local estable para cifrar credenciales n8n."
}

Write-Host "[setup] Validando Docker Compose..."
Invoke-Docker compose --profile lab config --quiet

$upArguments = @("compose", "--profile", "lab", "up", "-d", "--wait")
if (-not $NoBuild) {
    $upArguments += "--build"
}

Write-Host "[setup] Levantando el perfil LAB..."
Invoke-Docker @upArguments

Write-Host "[setup] Recalculando Attack Risk Score..."
Invoke-Docker compose exec -T pipeline-worker python /app/recalculate_risk_scores.py

& "$PSScriptRoot\configure_n8n_assets.ps1"

Write-Host "[setup] Entorno LAB listo."
