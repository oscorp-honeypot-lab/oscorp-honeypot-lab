param(
    [switch]$NoBuild
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "[smoke] Preparando LAB..."
& "$PSScriptRoot\setup.ps1" -NoBuild:$NoBuild

Write-Host "[smoke] Ejecutando demo integral..."
& "$PSScriptRoot\run_demo.ps1"

Write-Host "[smoke] Prueba integral superada."
