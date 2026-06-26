param(
    [string]$Host,
    [string]$User,
    [int]$SshPort,
    [string]$RemoteLogPath,
    [string]$LocalLogPath = "cowrie/logs/cowrie.json",
    [switch]$RunPipeline
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Get-DotEnvValue {
    param([string]$Name)

    if (-not (Test-Path -LiteralPath ".env")) {
        return $null
    }
    foreach ($line in Get-Content -LiteralPath ".env") {
        if ($line -match "^\s*$([regex]::Escape($Name))=(.*)$") {
            return $Matches[1].Trim()
        }
    }
    return $null
}

function Resolve-Setting {
    param(
        [string]$Value,
        [string]$EnvName,
        [string]$DefaultValue = ""
    )

    if (-not [string]::IsNullOrWhiteSpace($Value)) {
        return $Value
    }
    $fromEnv = [Environment]::GetEnvironmentVariable($EnvName)
    if (-not [string]::IsNullOrWhiteSpace($fromEnv)) {
        return $fromEnv
    }
    $fromDotEnv = Get-DotEnvValue -Name $EnvName
    if (-not [string]::IsNullOrWhiteSpace($fromDotEnv)) {
        return $fromDotEnv
    }
    return $DefaultValue
}

function Require-Command {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "No se encontro '$Name' en PATH. Instale OpenSSH Client o ejecute desde una terminal con scp disponible."
    }
}

function Invoke-Native {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$ErrorMessage
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw $ErrorMessage
    }
}

$Host = Resolve-Setting -Value $Host -EnvName "VPS_HOST"
$User = Resolve-Setting -Value $User -EnvName "VPS_USER" -DefaultValue "root"
$SshPortValue = if ($PSBoundParameters.ContainsKey("SshPort")) {
    [string]$SshPort
} else {
    Resolve-Setting -Value "" -EnvName "VPS_SSH_PORT" -DefaultValue "22"
}
$RemoteLogPath = Resolve-Setting -Value $RemoteLogPath -EnvName "VPS_COWRIE_LOG_PATH" -DefaultValue "/opt/oscorp-cowrie/logs/cowrie.json"

if ([string]::IsNullOrWhiteSpace($Host)) {
    throw "Defina VPS_HOST en .env o pase -Host."
}
if ([string]::IsNullOrWhiteSpace($User)) {
    throw "Defina VPS_USER en .env o pase -User."
}
if (-not [int]::TryParse($SshPortValue, [ref]$SshPort)) {
    throw "VPS_SSH_PORT debe ser numerico."
}
if ($SshPort -lt 1 -or $SshPort -gt 65535) {
    throw "VPS_SSH_PORT debe estar entre 1 y 65535."
}
if ($RemoteLogPath -notmatch "^/[A-Za-z0-9._/-]+$") {
    throw "VPS_COWRIE_LOG_PATH debe ser una ruta absoluta simple."
}

Require-Command -Name "scp"

$localFullPath = Join-Path $ProjectRoot $LocalLogPath
$localDirectory = Split-Path -Parent $localFullPath
if (-not (Test-Path -LiteralPath $localDirectory)) {
    New-Item -ItemType Directory -Path $localDirectory | Out-Null
}

$temporaryLog = Join-Path ([System.IO.Path]::GetTempPath()) "oscorp_cowrie_vps.json"
$remoteSpec = "{0}@{1}:{2}" -f $User, $Host, $RemoteLogPath

Write-Host "[vps-sync] Copiando $remoteSpec -> $LocalLogPath"
Write-Host "[vps-sync] Si usa password SSH, scp la pedira interactivamente."

try {
    Invoke-Native -FilePath "scp" `
        -Arguments @("-P", [string]$SshPort, $remoteSpec, $temporaryLog) `
        -ErrorMessage "No se pudo sincronizar el log de la VPS."

    Move-Item -LiteralPath $temporaryLog -Destination $localFullPath -Force
}
finally {
    Remove-Item -LiteralPath $temporaryLog -Force -ErrorAction SilentlyContinue
}

$bytes = (Get-Item -LiteralPath $localFullPath).Length
Write-Host "[vps-sync] Log sincronizado ($bytes bytes)."

if ($RunPipeline) {
    & "$PSScriptRoot\run_n8n_pipeline.ps1" -Profile real
    if ($LASTEXITCODE -ne 0) {
        throw "El pipeline finalizo con codigo $LASTEXITCODE."
    }
}
else {
    Write-Host "[vps-sync] Para procesar eventos REAL: .\scripts\run_n8n_pipeline.ps1 -Profile real"
}
