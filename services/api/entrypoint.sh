#!/bin/sh
set -e
export PYTHONPATH="/app/packages:/app/services:/app${PYTHONPATH:+:$PYTHONPATH}"
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
echo "Starting API..."
exec uvicorn api.main:app --host 0.0.0.0 --port 8000
