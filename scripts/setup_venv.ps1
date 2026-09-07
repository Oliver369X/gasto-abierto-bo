# Create / recreate project venv (Windows). Installs ONLY into .venv — never system Python.
# Usage:  powershell -File scripts\setup_venv.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$Py = Join-Path $env:USERPROFILE ".pyenv\pyenv-win\versions\3.12.5\python.exe"
if (-not (Test-Path $Py)) {
  $Py = Join-Path $env:USERPROFILE ".pyenv\pyenv-win\versions\3.12.0\python.exe"
}
if (-not (Test-Path $Py)) {
  Write-Error "No se encontro Python 3.12. Instala con: pyenv install 3.12.5"
}

Write-Host "Using: $Py"
& $Py --version

if (Test-Path .venv) {
  Write-Host "Removing old .venv ..."
  Remove-Item -Recurse -Force .venv
}

Write-Host "Creating .venv ..."
& $Py -m venv .venv

$python = Join-Path $PWD ".venv\Scripts\python.exe"

& $python -m pip install -U pip setuptools wheel
& $python -m pip install -e ".[dev]"

Write-Host ""
Write-Host "OK - entorno listo. Activa con:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host ('  $env:PYTHONPATH = "{0}\packages;{0}\services"' -f $PWD)
Write-Host "  pytest tests/contract tests/test_common.py -q"
Write-Host ""
Write-Host "Verificacion de producto: siempre Docker -> .\scripts\test_docker.ps1"
