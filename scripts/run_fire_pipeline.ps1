# AURA Incendios — pipeline Docker (Windows PowerShell)
# Uso: powershell -File .\scripts\run_fire_pipeline.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "== Fire pipeline (CLI worker.fire) ==" -ForegroundColor Cyan

$vols = @(
  "-v", "${Root}/packages:/app/packages",
  "-v", "${Root}/scripts:/app/scripts",
  "-v", "${Root}/services:/app/services",
  "-v", "${Root}/data:/app/data",
  "-v", "${Root}/tests:/app/tests",
  "-v", "${Root}/tests/fixtures:/app/tests/fixtures",
  "-v", "${Root}/docs:/app/docs"
)

$envArgs = @(
  "-e", "DATABASE_URL=postgresql+psycopg://gasto:gasto_dev_change_me@postgres:5432/gasto_abierto"
)

docker compose run --rm --no-deps @vols @envArgs --entrypoint sh api -c `
  "export PYTHONPATH=/app/packages:/app/services:/app && python -m scripts.cli fire pipeline --phase all"
if ($LASTEXITCODE -ne 0) { throw "pipeline failed" }

Write-Host "== verify ==" -ForegroundColor Cyan
docker compose run --rm --no-deps @vols `
  -e "API_BASE=http://api:8000" `
  -e "WEB_BASE=http://web:3000" `
  -e "DATABASE_URL=postgresql+psycopg://gasto:gasto_dev_change_me@postgres:5432/gasto_abierto" `
  --entrypoint sh api -c `
  "export PYTHONPATH=/app/packages:/app/services:/app && python -m scripts.cli fire verify"
if ($LASTEXITCODE -ne 0) { throw "verify failed" }

Write-Host "DONE — docs/aura-incendios/DOCKER.md" -ForegroundColor Green
