#!/bin/sh
set -e
export PYTHONPATH="/app/packages:/app/services:/app${PYTHONPATH:+:$PYTHONPATH}"
echo "Validating runtime env..."
python -c "from common.env_validate import validate_runtime_env; validate_runtime_env()"
echo "Starting ARQ worker..."
exec arq worker.main.WorkerSettings
