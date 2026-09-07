#!/usr/bin/env bash
# Definition of Success S1–S12 for Gasto Abierto Bolivia MVP
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PASS=0
FAIL=0
skip_docker="${SKIP_DOCKER:-0}"

ok() { echo "PASS $1"; PASS=$((PASS+1)); }
ko() { echo "FAIL $1 — $2"; FAIL=$((FAIL+1)); }

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
if command -v python >/dev/null 2>&1; then
  export PYTHONPATH="$ROOT/packages:$ROOT/services${PYTHONPATH:+:$PYTHONPATH}"
  if python -m pytest tests/contract tests/test_common.py -q --tb=line; then
    ok "S4:contract-tests"
  else
    ko "S4:contract-tests" "pytest failed"
  fi
else
  ko "S4:contract-tests" "python missing"
fi

# S1 / S2 / S3 / S7 / S8 via API if up
API="${API_URL:-http://localhost:8010}"
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
  if echo "$entities" | grep -q 'name'; then ok "S3:seed-entities"; else ko "S3:seed-entities" "empty"; fi
else
  if [[ "$skip_docker" == "1" ]]; then
    echo "SKIP S1/S7/S8 (API down, SKIP_DOCKER=1)"
  else
    ko "S1:api-health" "API not reachable at $API — run docker compose up"
  fi
fi

# S5 / S6 fixture paths exist (live optional)
if [[ -f tests/fixtures/agetic/sample_contracts.csv ]]; then ok "S5:agetic-fixture"; else ko "S5" "missing fixture"; fi
if [[ -f tests/fixtures/sicoes/procesos_sample.html ]]; then ok "S6:sicoes-fixture"; else ko "S6" "missing fixture"; fi

# S9 UI
WEB="${WEB_URL:-http://localhost:3010}"
if curl -sf "$WEB/" >/dev/null 2>&1; then ok "S9:web"; else
  if [[ "$skip_docker" == "1" ]]; then echo "SKIP S9"; else ko "S9:web" "web not up"; fi
fi

# S2 migrations file present
if [[ -f packages/schema/alembic/versions/0001_initial.py ]]; then ok "S2:migration-file"; else ko "S2" "missing"; fi

echo "----"
echo "Passed: $PASS  Failed: $FAIL"
if [[ "$FAIL" -gt 0 ]]; then exit 1; fi
exit 0
