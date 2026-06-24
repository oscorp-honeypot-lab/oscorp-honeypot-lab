$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$destination = Join-Path $ProjectRoot "backups\$timestamp"
New-Item -ItemType Directory -Path $destination -Force | Out-Null

Write-Host "[backup] Exportando PostgreSQL..."
$postgresDump = & docker compose exec -T postgres pg_dump -U oscorp -d oscorp
if ($LASTEXITCODE -ne 0) {
    throw "Falló el backup de PostgreSQL."
}
$postgresDump | Set-Content -LiteralPath (Join-Path $destination "postgres.sql") -Encoding UTF8

Write-Host "[backup] Exportando Elasticsearch..."
$searchBody = @{
    size = 10000
    query = @{ match_all = @{} }
} | ConvertTo-Json -Depth 5
$elasticData = Invoke-RestMethod `
    -Uri "http://localhost:9200/cowrie-events/_search" `
    -Method Post `
    -ContentType "application/json" `
    -Body $searchBody `
    -TimeoutSec 60
$elasticData | ConvertTo-Json -Depth 20 |
    Set-Content -LiteralPath (Join-Path $destination "elasticsearch.json") -Encoding UTF8

if (Test-Path -LiteralPath "cowrie\logs\cowrie.json") {
    Copy-Item -LiteralPath "cowrie\logs\cowrie.json" -Destination $destination
}
Copy-Item -LiteralPath "ESTADO_Y_ROADMAP.md" -Destination $destination

Write-Host "[backup] Backup creado en $destination"
