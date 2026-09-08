#!/usr/bin/env bash
# Definition of Success S1–S12 for Gasto Abierto Bolivia MVP
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source "$ROOT/scripts/_lib/loopback_host.sh"

PASS=0
FAIL=0
skip_docker="${SKIP_DOCKER:-0}"

ok() { echo "PASS $1"; PASS=$((PASS+1)); }
ko() { echo "FAIL $1 — $2"; FAIL=$((FAIL+1)); }

wait_url() {
  local url="$1"
  local label="$2"
  local max="${3:-60}"
  local sleep_s="${4:-5}"
  for _ in $(seq 1 "$max"); do
    if curl -sf "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$sleep_s"
  done
  return 1
}

maybe_start_stack() {
  if [[ "${VERIFY_START_SERVICES:-0}" != "1" ]]; then
    return 0
  fi
  if ! command -v docker >/dev/null 2>&1; then
    echo "VERIFY_START_SERVICES=1 but docker not found — skipping compose up"
    return 0
  fi
  if [[ ! -f docker-compose.yml ]]; then
    return 0
  fi
  echo "VERIFY_START_SERVICES=1 — ensuring docker compose stack is up..."
  if [[ ! -f .env ]]; then
    cp .env.example .env
  fi
  docker compose up -d --build
}

# Optional: host-side history seed when Docker RAM is tight (see scripts/host_seed_history.sh)
if [[ "${LOW_DOCKER_RAM:-0}" == "1" ]] && [[ "${HOST_SEED_HISTORY:-0}" == "1" ]]; then
  echo "LOW_DOCKER_RAM=1 — running host history seed before verify..."
  bash scripts/host_seed_history.sh || ko "S3:host-seed-history" "host seed failed"
fi

# S11 OSS hygiene
for f in LICENSE CONTRIBUTING.md CODE_OF_CONDUCT.md .env.example README.md; do
  if [[ -f "$f" ]]; then ok "S11:$f"; else ko "S11:$f" "missing"; fi
done

# S10 legal + sources
if [[ -f docs/legal/data-policy.md ]]; then ok "S10:data-policy"; else ko "S10:data-policy" "missing"; fi
for s in agetic sicoes presupuesto_abierto cge gad_scz gam_scz; do
  if [[ -f "docs/sources/$s.md" ]]; then ok "S10:source:$s"; else ko "S10:source:$s" "missing"; fi
done

# S4 contract tests offline
if command -v python3 >/dev/null 2>&1; then
  export PYTHONPATH="$ROOT/packages:$ROOT/services${PYTHONPATH:+:$PYTHONPATH}"
  if python3 -m pytest tests/contract tests/test_common.py -q --tb=line; then
    ok "S4:contract-tests"
  else
    ko "S4:contract-tests" "pytest failed"
  fi
elif command -v python >/dev/null 2>&1; then
  export PYTHONPATH="$ROOT/packages:$ROOT/services${PYTHONPATH:+:$PYTHONPATH}"
  if python -m pytest tests/contract tests/test_common.py -q --tb=line; then
    ok "S4:contract-tests"
  else
    ko "S4:contract-tests" "pytest failed"
  fi
else
  ko "S4:contract-tests" "python missing"
fi

maybe_start_stack

# S1 / S2 / S3 / S7 / S8 via API if up
API="${API_URL:-http://${_LOCAL_HOST}:8010}"
if ! curl -sf "$API/v1/health" >/dev/null 2>&1; then
  if [[ "$skip_docker" == "1" ]]; then
    echo "SKIP S1/S7/S8 (API down, SKIP_DOCKER=1)"
  else
    echo "Waiting for API at $API ..."
    if wait_url "$API/v1/health" "api" 60 5; then
      ok "S1:api-wait"
    else
      ko "S1:api-health" "API not reachable at $API — run docker compose up"
    fi
  fi
fi

  if curl -sf "$API/v1/health" >/dev/null 2>&1; then
  ok "S1:api-health"
  contracts=$(curl -sf "$API/v1/contracts" || true)
  if echo "$contracts" | grep -q '\['; then
    ok "S7:contracts"
    # provenance check S12
    if echo "$contracts" | grep -q 'source_id'; then ok "S12:provenance"; else ko "S12:provenance" "no source_id"; fi
  else
    ko "S7:contracts" "bad body"
  fi
  alerts=$(curl -sf "$API/v1/alerts" || true)
  if echo "$alerts" | grep -q 'explanation'; then ok "S8:alerts"; else ko "S8:alerts" "no explanation"; fi
  entities=$(curl -sf "$API/v1/entities" || true)
  if echo "$entities" | grep -q 'name'; then ok "S3:seed-entities"; else ko "S3:seed-entities" "empty — run: docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile history"; fi
  budgets=$(curl -sf "$API/v1/budgets/totals" || true)
  if echo "$budgets" | grep -q 'lines'; then ok "S13:budgets-totals"; else ko "S13:budgets-totals" "empty — seed history profile"; fi
  history=$(curl -sf "$API/v1/history/years" || true)
  if echo "$history" | grep -q 'year'; then ok "S14:history-years"; else ko "S14:history-years" "empty"; fi
  discs=$(curl -sf "$API/v1/discrepancies?limit=1" || true)
  if echo "$discs" | grep -q 'concept'; then ok "S15:discrepancies"; else ko "S15:discrepancies" "empty — seed publish or history+reconcile"; fi
  gate=$(curl -sf "$API/v1/product-gate" || true)
  if echo "$gate" | grep -q '"pass":true'; then ok "S16:product-gate"; else ko "S16:product-gate" "fail — run: gasto seed --profile publish"; fi
fi

# S5 / S6 / presupuesto fixtures
if [[ -f tests/fixtures/agetic/sample_contracts.csv ]]; then ok "S5:agetic-fixture"; else ko "S5" "missing fixture"; fi
if [[ -f tests/fixtures/sicoes/procesos_sample.html ]]; then ok "S6:sicoes-fixture"; else ko "S6" "missing fixture"; fi
if [[ -f tests/fixtures/presupuesto_abierto/sample_export.csv ]]; then ok "S6b:presupuesto-csv-fixture"; else ko "S6b" "missing presupuesto CSV fixture"; fi

# S9 UI — wait for web (Next.js cold start can exceed a single curl)
WEB="${WEB_URL:-http://${_LOCAL_HOST}:3010}"
if [[ "$skip_docker" == "1" ]]; then
  echo "SKIP S9"
elif wait_url "$WEB/" "web" 60 5; then
  ok "S9:web"
else
  ko "S9:web" "web not up at $WEB — run docker compose up -d web (or VERIFY_START_SERVICES=1)"
fi

# S2 migrations file present
if [[ -f packages/schema/alembic/versions/0001_initial.py ]]; then ok "S2:migration-file"; else ko "S2" "missing"; fi

echo "----"
echo "Passed: $PASS  Failed: $FAIL"
if [[ "$FAIL" -gt 0 ]]; then exit 1; fi
exit 0
