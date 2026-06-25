param(
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not $CheckOnly) {
    & "$PSScriptRoot\recalculate_risk_scores.ps1"
}

$result = (& docker compose exec -T postgres psql -U oscorp -d oscorp -At -F "|" -c @"
WITH invalid AS (
    SELECT COUNT(*) AS total
    FROM session_risk_scores
    WHERE rules_version = '1.0.0'
      AND (
          score NOT BETWEEN 0 AND 100
          OR risk_level <> CASE
              WHEN score <= 20 THEN 'low'
              WHEN score <= 50 THEN 'medium'
              WHEN score <= 80 THEN 'high'
              ELSE 'critical'
          END
          OR jsonb_typeof(reasons) <> 'array'
      )
),
counts AS (
    SELECT
        COUNT(*) AS total,
        COUNT(*) FILTER (WHERE risk_level = 'low') AS low,
        COUNT(*) FILTER (WHERE risk_level = 'medium') AS medium,
        COUNT(*) FILTER (WHERE risk_level = 'high') AS high,
        COUNT(*) FILTER (WHERE risk_level = 'critical') AS critical
    FROM session_risk_scores
    WHERE rules_version = '1.0.0'
)
SELECT
    (SELECT COUNT(*) FROM sessions),
    counts.total,
    invalid.total,
    counts.low,
    counts.medium,
    counts.high,
    counts.critical
FROM counts, invalid;
"@).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo consultar session_risk_scores."
}

$parts = $result -split "\|"
if ($parts.Count -ne 7 -or $parts[0] -ne $parts[1] -or $parts[2] -ne "0") {
    throw "Persistencia de Risk Score inconsistente: $result"
}

Write-Host "[risk] Scores válidos: $result"
