param(
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Assert-SessionProjection {
    $result = (& docker compose exec -T postgres psql -U oscorp -d oscorp -At -F "|" -c @"
WITH expected AS (
    SELECT COUNT(*) AS total
    FROM (
        SELECT COALESCE(sensor, 'unknown'), session_id
        FROM eventos
        WHERE session_id IS NOT NULL
        GROUP BY COALESCE(sensor, 'unknown'), session_id
    ) grouped
),
invalid AS (
    SELECT COUNT(*) AS total
    FROM sessions
    WHERE first_event_at > last_event_at
       OR duration_seconds < 0
       OR event_count < 0
       OR lifecycle_status NOT IN ('complete', 'open', 'incomplete')
)
SELECT
    (SELECT COUNT(*) FROM sessions),
    expected.total,
    invalid.total,
    (SELECT COALESCE(SUM(event_count), 0) FROM sessions),
    (SELECT COUNT(*) FROM eventos WHERE session_id IS NOT NULL)
FROM expected, invalid;
"@).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo consultar sessions."
    }
    $parts = $result -split "\|"
    if (
        $parts[0] -ne $parts[1] -or
        $parts[2] -ne "0" -or
        $parts[3] -ne $parts[4]
    ) {
        throw "Proyección de sesiones inconsistente: $result"
    }
    Write-Host "[sessions] Proyección válida: $result"
}

function Add-NdjsonLine {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Line
    )

    $absolutePath = Join-Path $ProjectRoot $Path
    $writer = [System.IO.StreamWriter]::new(
        $absolutePath,
        $true,
        [System.Text.UTF8Encoding]::new($false)
    )
    try {
        $writer.WriteLine($Line)
    }
    finally {
        $writer.Dispose()
    }
}

Assert-SessionProjection
if ($CheckOnly) {
    exit 0
}

$sessionId = "phase13-$([guid]::NewGuid().ToString('N').Substring(0, 12))"
$sensor = "phase13-validation"
$connectedAt = (Get-Date).ToUniversalTime()
$connect = @{
    eventid = "cowrie.session.connect"
    session = $sessionId
    sensor = $sensor
    src_ip = "198.51.100.13"
    src_port = 40113
    timestamp = $connectedAt.ToString("o")
} | ConvertTo-Json -Compress

& docker compose stop cowrie
try {
    Add-NdjsonLine -Path "cowrie\logs\cowrie.json" -Line $connect
}
finally {
    & docker compose up -d --wait cowrie
}
& "$PSScriptRoot\run_n8n_pipeline.ps1" | Out-Host

$openOutput = & docker compose exec -T postgres psql -U oscorp -d oscorp -At -c "SELECT lifecycle_status FROM sessions WHERE sensor='$sensor' AND session_id='$sessionId';"
if ($LASTEXITCODE -ne 0 -or $null -eq $openOutput) {
    throw "La sesión sintética no fue persistida."
}
$openStatus = ([string]$openOutput).Trim()
if ($openStatus -ne "open") {
    throw "Se esperaba sesión open y se obtuvo: $openStatus"
}

$closedAt = $connectedAt.AddSeconds(5)
$closed = @{
    eventid = "cowrie.session.closed"
    session = $sessionId
    sensor = $sensor
    src_ip = "198.51.100.13"
    timestamp = $closedAt.ToString("o")
} | ConvertTo-Json -Compress

& docker compose stop cowrie
try {
    Add-NdjsonLine -Path "cowrie\logs\cowrie.json" -Line $closed
}
finally {
    & docker compose up -d --wait cowrie
}
& "$PSScriptRoot\run_n8n_pipeline.ps1" | Out-Host

$completeOutput = & docker compose exec -T postgres psql -U oscorp -d oscorp -At -F "|" -c "SELECT lifecycle_status,event_count,duration_seconds FROM sessions WHERE sensor='$sensor' AND session_id='$sessionId';"
if ($LASTEXITCODE -ne 0 -or $null -eq $completeOutput) {
    throw "La sesión sintética cerrada no fue persistida."
}
$complete = ([string]$completeOutput).Trim()
if ($complete -notmatch "^complete\|2\|5(\.0+)?$") {
    throw "Transición open -> complete inválida: $complete"
}

Assert-SessionProjection
