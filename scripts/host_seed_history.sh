#!/usr/bin/env bash
# Seed history profile on the host when Docker has low RAM (avoids OOM in api container).
# Requires DATABASE_URL in .env (see .env.example).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Copy .env.example to .env first" >&2
  exit 1
fi

# shellcheck disable=SC1091
source .env 2>/dev/null || true

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL must be set in .env (see .env.example)" >&2
  exit 1
fi

export PYTHONPATH="$ROOT/packages:$ROOT/services${PYTHONPATH:+:$PYTHONPATH}"
export SEED_SKIP_STORAGE="${SEED_SKIP_STORAGE:-1}"
export SEED_SKIP_ALERTS_DURING_INGEST="${SEED_SKIP_ALERTS_DURING_INGEST:-1}"

echo "Host seed history — DATABASE_URL=${DATABASE_URL%%@*}@..."
python3 -m scripts.cli gasto seed --profile history
