param(
    [switch]$Once,
    [switch]$NoPipeline,
    [ValidateRange(30, 86400)]
    [int]$IntervalSeconds = 300,
    [ValidateRange(0, 1000000)]
    [int]$MaxIterations = 0,
    [ValidateRange(1, 10)]
    [int]$RetryCount = 3,
    [ValidateRange(5, 3600)]
    [int]$RetryDelaySeconds = 30,
    [string]$LogDirectory = "logs/real-sync"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Write-SyncLog {
    param(
        [string]$Message,
        [string]$Level = "info"
    )

    $timestamp = (Get-Date).ToString("s")
    $line = "[$timestamp][$Level] $Message"
    Write-Host $line
    Add-Content -LiteralPath $script:LogPath -Value $line
}

function Invoke-SyncOnce {
    $arguments = @()
    if (-not $NoPipeline) {
        $arguments += "-RunPipeline"
    }

    $output = & "$PSScriptRoot\sync_vps_logs.ps1" @arguments 2>&1
    $exitCode = $LASTEXITCODE
    foreach ($line in $output) {
        Write-SyncLog -Message ([string]$line)
    }
    if ($exitCode -ne 0) {
        throw "sync_vps_logs.ps1 finalizo con codigo $exitCode."
    }
}

$logRoot = Join-Path $ProjectRoot $LogDirectory
if (-not (Test-Path -LiteralPath $logRoot)) {
    New-Item -ItemType Directory -Path $logRoot | Out-Null
}
$script:LogPath = Join-Path $logRoot ("real-sync-" + (Get-Date).ToString("yyyyMMdd") + ".log")

$iteration = 0
do {
    $iteration += 1
    $success = $false
    for ($attempt = 1; $attempt -le $RetryCount -and -not $success; $attempt++) {
        try {
            Write-SyncLog -Message "Inicio de sincronizacion REAL iteracion=$iteration intento=$attempt."
            Invoke-SyncOnce
            Write-SyncLog -Message "Sincronizacion REAL completada iteracion=$iteration."
            $success = $true
        }
        catch {
            Write-SyncLog -Message $_.Exception.Message -Level "error"
            if ($attempt -lt $RetryCount) {
                Write-SyncLog -Message "Reintentando en $RetryDelaySeconds segundos."
                Start-Sleep -Seconds $RetryDelaySeconds
            }
        }
    }

    if (-not $success) {
        Write-SyncLog -Message "Sincronizacion REAL fallo despues de $RetryCount intentos." -Level "error"
    }

    if ($Once) {
        break
    }
    if ($MaxIterations -gt 0 -and $iteration -ge $MaxIterations) {
        break
    }

    Write-SyncLog -Message "Esperando $IntervalSeconds segundos hasta la proxima sincronizacion."
    Start-Sleep -Seconds $IntervalSeconds
} while ($true)
