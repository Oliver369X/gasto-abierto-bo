#!/usr/bin/env bash
# Create / recreate project venv. Installs ONLY into .venv — never system site-packages.
set -euo pipefail
cd "$(dirname "$0")/.."

PY=""
if command -v python3.12 >/dev/null 2>&1; then
  PY=python3.12
elif [[ -x "${HOME}/.pyenv/versions/3.12.5/bin/python" ]]; then
  PY="${HOME}/.pyenv/versions/3.12.5/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  echo "Need Python >=3.11 (prefer 3.12 to match Docker)" >&2
  exit 1
fi

echo "Using: $($PY --version)"
rm -rf .venv
"$PY" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -U pip setuptools wheel
pip install -e ".[dev]"
export PYTHONPATH="$PWD/packages:$PWD/services"
echo "OK. Activate: source .venv/bin/activate"
echo "Product verify: ./scripts/test_docker.sh"
