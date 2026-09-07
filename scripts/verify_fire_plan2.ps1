# Verificación Plan 2 / gates AURA Incendios
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$vols = @(
  "-v", "${Root}/packages:/app/packages",
  "-v", "${Root}/scripts:/app/scripts",
  "-v", "${Root}/services:/app/services",
  "-v", "${Root}/data:/app/data",
  "-v", "${Root}/docs:/app/docs",
  "-v", "${Root}/tests:/app/tests"
)

Write-Host "== pytest fire (unit) ==" -ForegroundColor Cyan
docker compose run --rm --no-deps @vols `
  -e "DATABASE_URL=postgresql+psycopg://gasto:gasto_dev_change_me@postgres:5432/gasto_abierto" `
  --entrypoint sh api -c `
  "export PYTHONPATH=/app/packages:/app/services:/app && pytest tests/test_fire_ledger_f1.py tests/test_fire_classify.py tests/test_fire_classify_golden.py tests/test_fire_rollup.py tests/test_fire_phase_scripts.py tests/test_fire_sernap_extract.py tests/test_fire_capability.py tests/test_fire_geo_bbox.py tests/test_fire_gaceta_adapters.py -q --tb=line"
if ($LASTEXITCODE -ne 0) { throw "pytest fire failed" }

Write-Host "== verify CLI ==" -ForegroundColor Cyan
docker compose run --rm --no-deps @vols `
  -e "API_BASE=http://api:8000" `
  -e "WEB_BASE=http://web:3000" `
  -e "DATABASE_URL=postgresql+psycopg://gasto:gasto_dev_change_me@postgres:5432/gasto_abierto" `
  --entrypoint sh api -c `
  "export PYTHONPATH=/app/packages:/app/services:/app && python -m scripts.cli fire verify"
if ($LASTEXITCODE -ne 0) { throw "verify failed" }

Write-Host "ALL CHECKS PASSED" -ForegroundColor Green
