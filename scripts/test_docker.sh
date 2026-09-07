#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[[ -f .env ]] || cp .env.example .env
docker compose up -d postgres redis minio minio-init api
docker compose run --rm --no-deps --entrypoint /bin/sh api /app/scripts/run_docker_tests.sh
echo "ALL OK"
