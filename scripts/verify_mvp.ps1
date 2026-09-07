# Gasto Abierto Bolivia - verify helper for Windows PowerShell
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONPATH = "$Root\packages;$Root\services"
$script:Pass = 0
$script:Fail = 0

function Ok([string]$msg) { Write-Host "PASS $msg"; $script:Pass++ }
function Ko([string]$msg, [string]$why) { Write-Host "FAIL $msg - $why"; $script:Fail++ }

foreach ($f in @("LICENSE","CONTRIBUTING.md","CODE_OF_CONDUCT.md",".env.example","README.md")) {
  if (Test-Path $f) { Ok "S11:$f" } else { Ko "S11:$f" "missing" }
}
if (Test-Path "docs\legal\data-policy.md") { Ok "S10:data-policy" } else { Ko "S10:data-policy" "missing" }
foreach ($s in @("agetic","sicoes","presupuesto_abierto","cge","gad_scz","gam_scz","mindef","abt","fire-inventory","gaceta_scz","sernap","firms")) {
  if (Test-Path "docs\sources\$s.md") { Ok "S10:source:$s" } else { Ko "S10:source:$s" "missing" }
}

# Prefer Docker suite when available; host pytest only as fallback (use .venv)
$PyTest = $null
if (Test-Path ".\.venv\Scripts\python.exe") {
  $PyTest = ".\.venv\Scripts\python.exe"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  $PyTest = "python"
}

if ($env:VERIFY_HOST_PYTEST -eq "1" -or $PyTest) {
  Write-Host "HINT: for full Docker suite run .\scripts\test_docker.ps1"
  if ($PyTest) {
    $env:PYTHONPATH = "$Root\packages;$Root\services"
    & $PyTest -m pytest tests/contract tests/test_common.py tests/test_proxy.py tests/test_history_fixture.py tests/test_pipeline_resilience.py tests/test_categorize.py -q --tb=line
    if ($LASTEXITCODE -eq 0) { Ok "S4:contract-tests" } else { Ko "S4:contract-tests" "pytest failed (use test_docker.ps1)" }
  } else {
    Write-Host "SKIP host pytest - use scripts/test_docker.ps1"
  }
}

$Api = if ($env:API_URL) { $env:API_URL } else { "http://localhost:8010" }
try {
  $h = Invoke-RestMethod "$Api/v1/health"
  if ($h.status -eq "ok") { Ok "S1:api-health" } else { Ko "S1:api-health" "bad status" }
  if ($null -ne $h.proxy) { Ok "S13:proxy-status" } else { Ko "S13:proxy-status" "missing proxy block" }
  $c = Invoke-RestMethod "$Api/v1/contracts"
  if ($null -ne $c) { Ok "S7:contracts" } else { Ko "S7:contracts" "null" }
  if (($c | Select-Object -First 1).source_id) { Ok "S12:provenance" } else { Ko "S12:provenance" "no source_id" }
  $a = Invoke-RestMethod "$Api/v1/alerts"
  if (($a | Select-Object -First 1).explanation) { Ok "S8:alerts" } else { Ko "S8:alerts" "no alerts" }
  $e = Invoke-RestMethod "$Api/v1/entities"
  if (($e | Select-Object -First 1).name) { Ok "S3:seed-entities" } else { Ko "S3:seed-entities" "empty" }
  $hy = Invoke-RestMethod "$Api/v1/history/years"
  if (($hy | Measure-Object).Count -ge 2) { Ok "S14:history-years" } else { Ko "S14:history-years" "need multi-year series" }
  $coldUrl = $Api + '/v1/contracts?year=2019&include_history=true'
  $cold = Invoke-RestMethod $coldUrl
  if (($cold | Measure-Object).Count -ge 1) { Ok "S14:contracts-2019" } else { Ko "S14:contracts-2019" "empty" }
  $cats = Invoke-RestMethod "$Api/v1/categories"
  if (($cats | Measure-Object).Count -ge 5) { Ok "S15:categories" } else { Ko "S15:categories" "missing catalog" }
  $sr = Invoke-RestMethod ($Api + '/v1/search?q=Santa')
  if (($sr.hits | Measure-Object).Count -ge 1) { Ok "S16:search" } else { Ko "S16:search" "no hits" }
  $cmp = Invoke-RestMethod ($Api + '/v1/history/compare?year_a=2024&year_b=2025')
  if ($null -ne $cmp.amount_delta_pct -or $cmp.contracts_b -ge 0) { Ok "S16:history-compare" } else { Ko "S16:history-compare" "bad" }
} catch {
  if ($env:SKIP_DOCKER -eq "1") { Write-Host "SKIP API checks" } else { Ko "S1:api-health" $_.Exception.Message }
}

if (Test-Path "tests\fixtures\agetic\sample_contracts.csv") { Ok "S5:agetic-fixture" } else { Ko "S5" "missing" }
if (Test-Path "tests\fixtures\sicoes\procesos_sample.html") { Ok "S6:sicoes-fixture" } else { Ko "S6" "missing" }
if (Test-Path "tests\fixtures\agetic\contracts_history_2019_2025.csv") { Ok "S14:history-fixture" } else { Ko "S14:history-fixture" "missing" }

$Web = if ($env:WEB_URL) { $env:WEB_URL } else { "http://localhost:3010" }
if ($env:SKIP_DOCKER -eq "1") {
  Write-Host "SKIP S9"
} else {
  try {
    Invoke-WebRequest "$Web/" -UseBasicParsing -TimeoutSec 5 | Out-Null
    Ok "S9:web"
    Invoke-WebRequest "$Web/historico" -UseBasicParsing -TimeoutSec 5 | Out-Null
    Ok "S14:web-historico"
    Invoke-WebRequest "$Web/incendios" -UseBasicParsing -TimeoutSec 8 | Out-Null
    Ok "S15:web-incendios"
  } catch {
    Ko "S9:web" $_.Exception.Message
  }
}

try {
  $ledger = Invoke-RestMethod "$Api/v1/fire/ledger?year=2024" -TimeoutSec 10
  if ($null -ne $ledger.amount_direct_verifiable) { Ok "S15:fire-ledger" } else { Ko "S15:fire-ledger" "missing field" }
} catch {
  Ko "S15:fire-ledger" $_.Exception.Message
}

if (Test-Path "packages\schema\alembic\versions\0001_initial.py") { Ok "S2:migration-file" } else { Ko "S2" "missing" }
if (Test-Path "packages\schema\alembic\versions\0004_fire_ledger.py") { Ok "S15:migration-fire" } else { Ko "S15:migration-fire" "missing" }

Write-Host "----"
Write-Host "Passed: $Pass  Failed: $Fail"
if ($Fail -gt 0) { exit 1 }
exit 0
