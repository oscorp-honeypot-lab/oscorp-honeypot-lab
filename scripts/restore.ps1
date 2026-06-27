param(
    [Parameter(Mandatory = $true)]
    [string]$BackupPath
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

$resolved = Resolve-Path -LiteralPath $BackupPath -ErrorAction Stop
$sqlFile = Join-Path $resolved "postgres.sql"

if (-not (Test-Path -LiteralPath $sqlFile)) {
    throw "No se encontró postgres.sql en: $resolved"
}

Write-Host "[restore] Restaurando desde: $resolved"

# Detener todo el stack salvo postgres para evitar escrituras concurrentes.
Write-Host "[restore] Deteniendo servicios (excepto postgres)..."
Invoke-Docker compose --profile lab stop `
    n8n pipeline-worker backend frontend kibana elasticsearch cowrie attacker-sim payload-server

# El dump fue generado con --clean --if-exists, por lo que incluye
# DROP TABLE IF EXISTS antes de cada CREATE TABLE.
Write-Host "[restore] Restaurando PostgreSQL..."
$sqlContent = Get-Content -LiteralPath $sqlFile -Raw -Encoding UTF8
$sqlContent | & docker compose exec -T postgres psql -U oscorp -d oscorp
if ($LASTEXITCODE -ne 0) {
    throw "Falló la restauración de PostgreSQL."
}

# Restaurar cowrie.json si existe en el backup.
$cowrieFile = Join-Path $resolved "cowrie.json"
if (Test-Path -LiteralPath $cowrieFile) {
    Write-Host "[restore] Restaurando cowrie.json..."
    Copy-Item -LiteralPath $cowrieFile -Destination "cowrie\logs\cowrie.json" -Force
}

# Reiniciar todo el stack.
Write-Host "[restore] Reiniciando el perfil LAB..."
Invoke-Docker compose --profile lab up -d --wait

# Reconstruir Elasticsearch: borrar el índice y resetear el checkpoint a 0,
# luego correr el pipeline que re-lee cowrie.json e indexa todo desde cero.
Write-Host "[restore] Borrando índice Elasticsearch para reconstrucción..."
$null = Invoke-RestMethod `
    -Uri "http://localhost:9200/cowrie-events" `
    -Method Delete `
    -ErrorAction SilentlyContinue

Write-Host "[restore] Reseteando checkpoint del pipeline a offset 0..."
& docker compose exec -T postgres psql -U oscorp -d oscorp `
    -c "UPDATE pipeline_checkpoints SET byte_offset = 0, last_line = 0;" | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Warning "[restore] No se pudo resetear el checkpoint."
}

Write-Host "[restore] Ejecutando pipeline para re-indexar en Elasticsearch..."
& "$PSScriptRoot\run_n8n_pipeline.ps1" -Profile lab
if ($LASTEXITCODE -ne 0) {
    Write-Warning "[restore] El pipeline finalizó con errores. Verificar manualmente."
}

Write-Host "[restore] Restauración completada."
Write-Host "[restore] Verificando estado del LAB..."
& "$PSScriptRoot\validate_lab.ps1"
