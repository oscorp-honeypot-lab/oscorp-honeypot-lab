$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Assert-Command {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "No se encontro '$Name' en PATH."
    }
}

function Assert-File {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Falta el archivo requerido: $Path"
    }
}

Write-Host "[real] Verificando herramientas locales..."
Assert-Command -Name "ssh"
Assert-Command -Name "scp"
Assert-Command -Name "docker"

Write-Host "[real] Verificando artefactos REAL..."
Assert-File -Path "scripts/setup_vps.ps1"
Assert-File -Path "scripts/sync_vps_logs.ps1"
Assert-File -Path "scripts/setup_real.ps1"
Assert-File -Path "scripts/run_real_sync.ps1"
Assert-File -Path "docs/arquitectura-vps.md"

Write-Host "[real] Validando sintaxis PowerShell..."
$scripts = @(
    "scripts/setup_vps.ps1",
    "scripts/sync_vps_logs.ps1",
    "scripts/setup_real.ps1",
    "scripts/run_real_sync.ps1",
    "scripts/run_n8n_pipeline.ps1",
    "scripts/validate_real_mode.ps1"
)
foreach ($script in $scripts) {
    [scriptblock]::Create((Get-Content -Raw -LiteralPath $script)) | Out-Null
}

Write-Host "[real] Validando Docker Compose perfil real..."
docker compose --profile real config --quiet
if ($LASTEXITCODE -ne 0) {
    throw "docker compose --profile real config fallo."
}

$services = docker compose --profile real config --services
if ($LASTEXITCODE -ne 0) {
    throw "No se pudieron listar servicios del perfil real."
}
$forbidden = @("cowrie", "attacker-sim", "payload-server")
foreach ($service in $forbidden) {
    if ($services -contains $service) {
        throw "El perfil real no debe incluir el servicio local '$service'."
    }
}

Write-Host "[real] Verificando que no se versionen passwords de VPS..."
$envExample = Get-Content -Raw -LiteralPath ".env.example"
if ($envExample -match "VPS_PASSWORD|VPS_PASS|ROOT_PASSWORD") {
    throw ".env.example no debe declarar passwords de VPS."
}

Write-Host "[real] Modo REAL validado sin conectar a ninguna VPS."
