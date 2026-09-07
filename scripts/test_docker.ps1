# Run the full offline+history test suite INSIDE Docker (required).
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path .env)) { Copy-Item .env.example .env }

Write-Host "== ensuring core services =="
docker compose up -d postgres redis minio minio-init api

Write-Host "== docker test suite (reuse api image, no rebuild) =="
docker compose run --rm --no-deps --entrypoint /bin/sh api /app/scripts/run_docker_tests.sh
if ($LASTEXITCODE -ne 0) {
  # image may be stale — rebuild once then retry
  Write-Host "== rebuilding api image then retry =="
  docker compose build api
  docker compose up -d --force-recreate api
  Start-Sleep -Seconds 25
  docker compose run --rm --no-deps --entrypoint /bin/sh api /app/scripts/run_docker_tests.sh
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "ALL OK"
