$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) {
        throw "[audit] FALLO: $Message"
    }
    Write-Host "[audit] OK: $Message"
}

Write-Host "[audit] Iniciando validación de reproducibilidad y seguridad..."

# ── 1. Secretos no versionados ───────────────────────────────────────────────
Write-Host "[audit] Verificando que .env no esté en git..."
$trackedEnv = & git ls-files ".env" 2>&1
Assert-True ([string]::IsNullOrEmpty($trackedEnv)) ".env no debe estar versionado en git"

Write-Host "[audit] Verificando que no haya secretos hardcodeados en .env.example..."
$envExample = Get-Content ".env.example" -Raw
# Usar \S+ para evitar que \r (carriage return de Windows) haga match falso positivo
Assert-True ($envExample -notmatch "N8N_ENCRYPTION_KEY=\S+") `
    "N8N_ENCRYPTION_KEY debe estar vacío en .env.example"
Assert-True ($envExample -notmatch "OSCORP_API_ADMIN_PASSWORD=\S+") `
    "OSCORP_API_ADMIN_PASSWORD debe estar vacío en .env.example"
Assert-True ($envExample -notmatch "VPS_HOST=\S+") `
    "VPS_HOST debe estar vacío en .env.example"

Write-Host "[audit] Verificando que cowrie/logs/*.json no esté versionado..."
$trackedLogs = & git ls-files "cowrie/logs/*.json" 2>&1
Assert-True ([string]::IsNullOrEmpty($trackedLogs)) "cowrie/logs/*.json no debe estar versionado"

Write-Host "[audit] Verificando que backups/ no esté versionado..."
$trackedBackups = & git ls-files "backups/*.sql" "backups/*.json" 2>&1
Assert-True ([string]::IsNullOrEmpty($trackedBackups)) "backups/ no debe estar versionado"

# ── 2. Pinning de imágenes Docker externas ───────────────────────────────────
Write-Host "[audit] Verificando pinning de imágenes Docker externas..."
$composeContent = Get-Content "docker-compose.yml" -Raw
$externalImages = ($composeContent -split "`n") | Where-Object {
    $_ -match "^\s+image:\s+\S+" -and $_ -notmatch "oscorp/"
}
foreach ($line in $externalImages) {
    Assert-True ($line -match "@sha256:") `
        "Imagen externa sin digest: $($line.Trim())"
}

# ── 3. Pinning de dependencias Python ────────────────────────────────────────
Write-Host "[audit] Verificando pinning de dependencias Python..."
foreach ($reqFile in @("pipeline/requirements.txt", "backend/requirements.txt")) {
    $lines = Get-Content $reqFile | Where-Object { $_ -match "\S" -and $_ -notmatch "^\s*#" }
    foreach ($line in $lines) {
        Assert-True ($line -match "==\d") `
            "$reqFile línea sin pin exacto: $line"
    }
}

# ── 4. Docker Compose válido para ambos perfiles ─────────────────────────────
Write-Host "[audit] Verificando configuración Docker Compose..."
$dockerFound = $null -ne (Get-Command "docker" -ErrorAction SilentlyContinue)
if ($dockerFound) {
    & docker compose --profile lab config --quiet
    Assert-True ($LASTEXITCODE -eq 0) "Docker Compose perfil lab es válido"

    & docker compose --profile real config --quiet
    Assert-True ($LASTEXITCODE -eq 0) "Docker Compose perfil real es válido"
} else {
    Write-Warning "[audit] docker no encontrado en PATH. Omitiendo verificación de compose config."
    Write-Warning "[audit] Ejecutar desde PowerShell con Docker Desktop disponible."
}

# ── 5. Tests de auditoría Python ─────────────────────────────────────────────
Write-Host "[audit] Ejecutando tests de auditoría de seguridad (Python)..."
$pythonExe = "python"
if (-not (Get-Command $pythonExe -ErrorAction SilentlyContinue)) {
    $pythonExe = "python3"
}
if (Get-Command $pythonExe -ErrorAction SilentlyContinue) {
    $env:PYTHONPATH = Join-Path $ProjectRoot "scripts"
    & $pythonExe -m unittest discover `
        -s (Join-Path $ProjectRoot "pipeline\tests") `
        -p "test_security_audit.py" -v
    if ($LASTEXITCODE -ne 0) {
        throw "Tests de auditoría de seguridad fallaron."
    }
    Write-Host "[audit] OK: Tests de auditoría superados"
} else {
    Write-Warning "[audit] Python no disponible en el host. Tests de auditoría omitidos."
    Write-Warning "[audit] Ejecutar en CI o con Python instalado localmente."
}

# ── 6. Estado operativo del LAB ──────────────────────────────────────────────
Write-Host "[audit] Verificando estado operativo del LAB..."
if ($dockerFound) {
    & "$PSScriptRoot\validate_lab.ps1"
} else {
    Write-Warning "[audit] docker no encontrado. Omitiendo validate_lab.ps1."
    Write-Warning "[audit] Ejecutar .\scripts\validate_lab.ps1 desde PowerShell."
}

Write-Host ""
Write-Host "[audit] Validación de reproducibilidad y seguridad superada."
