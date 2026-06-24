param(
    [string]$Python = "C:\Users\GAMER\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe",
    [string]$LogPath = "cowrie\logs\cowrie.json",
    [string]$ElasticsearchUrl = "http://localhost:9200",
    [string]$ElasticsearchIndex = "cowrie-events"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Python)) {
    $Python = "python"
}

& $Python scripts\process_cowrie_ndjson.py `
    --log $LogPath `
    --project-dir . `
    --elasticsearch-url $ElasticsearchUrl `
    --elasticsearch-index $ElasticsearchIndex
