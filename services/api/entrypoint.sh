#!/bin/sh
set -e
export PYTHONPATH="/app/packages:/app/services:/app${PYTHONPATH:+:$PYTHONPATH}"
echo "Validating runtime env..."
python -c "from common.env_validate import validate_runtime_env; validate_runtime_env()"
echo "Running migrations..."
alembic upgrade head
echo "Seeding demo data..."
python -m scripts.cli gasto seed --profile demo
# Heavy boot seeds are optional — they blocked API startup when hung.
if [ "${BOOT_FULL_SEED:-0}" = "1" ]; then
  echo "BOOT_FULL_SEED=1 — running history/category/cross seeds..."
  python -m scripts.cli gasto seed --profile history || true
  python scripts/_legacy/backfill_categories.py || true
  python -m scripts.cli gasto seed --profile cross || true
else
  echo "Skipping heavy boot seeds (set BOOT_FULL_SEED=1 to enable)"
fi
if [ "${BOOT_PUBLISH_SEED:-0}" = "1" ]; then
  echo "BOOT_PUBLISH_SEED=1 — running publish seed (product-gate + incendios)..."
  python -m scripts.cli gasto seed --profile publish || true
else
  echo "Skipping publish seed (set BOOT_PUBLISH_SEED=1 for product-gate + incendios on boot)"
fi
API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8000}"
echo "Starting API on ${API_HOST}:${API_PORT}..."
exec uvicorn api.main:app --host "$API_HOST" --port "$API_PORT"
