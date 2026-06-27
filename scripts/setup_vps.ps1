param(
    [string]$VpsHost,
    [string]$User,
    [int]$SshPort,
    [string]$RemoteDir,
    [int]$CowriePort,
    [switch]$SkipFirewall,
    [switch]$AssumeYes
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
        throw "No se encontro '$Name' en PATH. Instale OpenSSH Client o ejecute desde una terminal con ssh/scp disponible."
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

function ConvertTo-BashSingleQuote {
    param([string]$Value)

    return "'" + ($Value -replace "'", "'\''") + "'"
}

$VpsHost = Resolve-Setting -Value $VpsHost -EnvName "VPS_HOST"
$User = Resolve-Setting -Value $User -EnvName "VPS_USER" -DefaultValue "root"
$SshPortValue = if ($PSBoundParameters.ContainsKey("SshPort")) {
    [string]$SshPort
} else {
    Resolve-Setting -Value "" -EnvName "VPS_SSH_PORT" -DefaultValue "22"
}
$RemoteDir = Resolve-Setting -Value $RemoteDir -EnvName "VPS_REMOTE_DIR" -DefaultValue "/opt/oscorp-cowrie"
$CowriePortValue = if ($PSBoundParameters.ContainsKey("CowriePort")) {
    [string]$CowriePort
} else {
    Resolve-Setting -Value "" -EnvName "VPS_COWRIE_SSH_PORT" -DefaultValue "2222"
}

if ([string]::IsNullOrWhiteSpace($VpsHost)) {
    throw "Defina VPS_HOST en .env o pase -VpsHost."
}
if ([string]::IsNullOrWhiteSpace($User)) {
    throw "Defina VPS_USER en .env o pase -User."
}
if (-not [int]::TryParse($SshPortValue, [ref]$SshPort)) {
    throw "VPS_SSH_PORT debe ser numerico."
}
if (-not [int]::TryParse($CowriePortValue, [ref]$CowriePort)) {
    throw "VPS_COWRIE_SSH_PORT debe ser numerico."
}
if ($SshPort -lt 1 -or $SshPort -gt 65535) {
    throw "VPS_SSH_PORT debe estar entre 1 y 65535."
}
if ($CowriePort -lt 1024 -or $CowriePort -gt 65535) {
    throw "VPS_COWRIE_SSH_PORT debe estar entre 1024 y 65535 para no tocar SSH administrativo."
}
if ($RemoteDir -notmatch "^/[A-Za-z0-9._/-]+$") {
    throw "VPS_REMOTE_DIR debe ser una ruta absoluta simple, sin espacios ni caracteres especiales."
}

Require-Command -Name "ssh"
Require-Command -Name "scp"

Write-Host "[vps] Objetivo: $User@$VpsHost puerto SSH $SshPort"
Write-Host "[vps] Cowrie quedara publicado en el puerto TCP $CowriePort de la VPS."
Write-Host "[vps] No se guardan contrasenas en el repo. Si usa password SSH, ssh/scp la pediran interactivamente."

if (-not $AssumeYes) {
    $confirmation = Read-Host "Escriba SETUP-VPS para configurar ese servidor"
    if ($confirmation -ne "SETUP-VPS") {
        throw "Operacion cancelada."
    }
}

$remoteDirLiteral = ConvertTo-BashSingleQuote -Value $RemoteDir
$skipFirewallValue = if ($SkipFirewall) { "1" } else { "0" }
$remoteScript = @"
#!/bin/bash
set -eu

REMOTE_DIR=$remoteDirLiteral
COWRIE_PORT=$CowriePort
SKIP_FIREWALL=$skipFirewallValue

if [ "`$(id -u)" -ne 0 ]; then
  SUDO=sudo
else
  SUDO=
fi

echo "[vps] Preparando paquetes base..."
export DEBIAN_FRONTEND=noninteractive
`$SUDO apt-get update
`$SUDO apt-get install -y ca-certificates curl docker.io docker-compose-v2 ufw
`$SUDO systemctl enable --now docker

if ! docker compose version >/dev/null 2>&1; then
  echo "[vps] docker compose no esta disponible despues de instalar docker-compose-v2." >&2
  exit 1
fi

echo "[vps] Creando directorios en `$REMOTE_DIR..."
`$SUDO mkdir -p "`$REMOTE_DIR/logs"
`$SUDO chown -R 1000:1000 "`$REMOTE_DIR/logs"
`$SUDO chmod 0775 "`$REMOTE_DIR/logs"

echo "[vps] Escribiendo docker-compose.yml de Cowrie..."
`$SUDO tee "`$REMOTE_DIR/docker-compose.yml" >/dev/null <<'YAML'
services:
  cowrie:
    image: cowrie/cowrie:3.0.0@sha256:f5ee0f7d0171cb5d924ae9a96eeb7a3fef876f0217b4052ea22dc3f779691ebe
    container_name: oscorp_vps_cowrie
    restart: unless-stopped
    ports:
      - "`${COWRIE_PUBLIC_PORT:-2222}:2222"
    volumes:
      - ./logs:/cowrie/cowrie-git/var/log/cowrie
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
YAML

`$SUDO tee "`$REMOTE_DIR/.env" >/dev/null <<ENV
COWRIE_PUBLIC_PORT=`$COWRIE_PORT
ENV

echo "[vps] Levantando Cowrie..."
cd "`$REMOTE_DIR"
`$SUDO docker compose --env-file .env up -d

if [ "`$SKIP_FIREWALL" != "1" ] && command -v ufw >/dev/null 2>&1; then
  echo "[vps] Configurando UFW sin habilitarlo si estaba inactivo..."
  `$SUDO ufw allow OpenSSH >/dev/null || true
  `$SUDO ufw allow "`$COWRIE_PORT/tcp" >/dev/null || true
  if `$SUDO ufw status | grep -qi "Status: active"; then
    `$SUDO ufw reload >/dev/null || true
  else
    echo "[vps] UFW esta inactivo; se dejaron reglas cargadas pero no se habilito automaticamente."
  fi
fi

echo "[vps] Validando contenedor..."
for attempt in `$(seq 1 12); do
  running=`$(`$SUDO docker inspect -f '{{.State.Running}}' oscorp_vps_cowrie 2>/dev/null || true)
  if [ "`$running" = "true" ]; then
    break
  fi
  sleep 5
done

running=`$(`$SUDO docker inspect -f '{{.State.Running}}' oscorp_vps_cowrie 2>/dev/null || true)
if [ "`$running" != "true" ]; then
  `$SUDO docker logs --tail=80 oscorp_vps_cowrie || true
  echo "[vps] Cowrie no quedo en ejecucion." >&2
  exit 1
fi

`$SUDO touch "`$REMOTE_DIR/logs/cowrie.json"
`$SUDO chown 1000:1000 "`$REMOTE_DIR/logs/cowrie.json"

echo "[vps] OK. Cowrie escucha en el puerto `$COWRIE_PORT y escribe en `$REMOTE_DIR/logs/cowrie.json"
"@

$temporaryScript = Join-Path ([System.IO.Path]::GetTempPath()) "oscorp_setup_vps.sh"
[System.IO.File]::WriteAllText($temporaryScript, $remoteScript, [System.Text.UTF8Encoding]::new($false))

$sshTarget = "$User@$VpsHost"
$remoteTmp = "/tmp/oscorp_setup_vps.sh"
$sshBaseArgs = @("-p", [string]$SshPort, "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=4", $sshTarget)

try {
    Invoke-Native -FilePath "scp" `
        -Arguments @("-P", [string]$SshPort, $temporaryScript, ("{0}:{1}" -f $sshTarget, $remoteTmp)) `
        -ErrorMessage "No se pudo copiar el instalador a la VPS."

    Invoke-Native -FilePath "ssh" `
        -Arguments ($sshBaseArgs + @("bash", $remoteTmp)) `
        -ErrorMessage "La configuracion remota de la VPS fallo."
}
finally {
    Remove-Item -LiteralPath $temporaryScript -Force -ErrorAction SilentlyContinue
}

Write-Host "[vps] Configuracion finalizada."
Write-Host "[vps] Para traer logs al LAB local: .\scripts\sync_vps_logs.ps1"
