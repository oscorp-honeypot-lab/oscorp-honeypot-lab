param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not $Force) {
    $confirmation = Read-Host "Esto eliminará volúmenes y logs LAB. Escriba RESET para continuar"
    if ($confirmation -ne "RESET") {
        Write-Host "Operación cancelada."
        exit 0
    }
}

docker compose --profile lab --profile tools down --volumes --remove-orphans
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo detener y limpiar el LAB."
}

Get-ChildItem -LiteralPath "cowrie\logs" -File |
    Where-Object { $_.Name -ne ".gitkeep" } |
    Remove-Item -Force

Write-Host "LAB reiniciado. Ejecute .\scripts\setup.ps1 para crearlo nuevamente."
