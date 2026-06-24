$ErrorActionPreference = "Stop"

docker compose --profile lab --profile tools run --rm pipeline

if ($LASTEXITCODE -ne 0) {
    throw "El pipeline finalizó con código $LASTEXITCODE."
}
