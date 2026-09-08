#!/usr/bin/env bash
# Staging readiness: curl /v1/health, /v1/product-gate, /v1/budgets/totals.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  set -a
  # Export only simple KEY=VALUE lines (ignore comments).
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]] && export "$line"
  done < .env
  set +a
fi

API_HOST_PORT="${API_HOST_PORT:-8010}"
API="${STAGING_API_URL:-${API_URL:-http://127.0.0.1:${API_HOST_PORT}}}"  # pragma: allowlist secret

PASS=0
FAIL=0
ok() { echo "OK  $1"; PASS=$((PASS + 1)); }
ko() { echo "FAIL $1 — $2"; FAIL=$((FAIL + 1)); }

echo "Staging check → $API"

health=$(curl -sf "$API/v1/health" 2>/dev/null || true)
if echo "$health" | grep -q '"status":"ok"'; then
  ok "GET /v1/health"
  if [[ "${LIVE_SCRAPE:-0}" == "1" ]]; then
    if echo "$health" | grep -q '"proxy_configured":true'; then
      ok "proxy (LIVE_SCRAPE=1)"
    else
      ko "proxy" "LIVE_SCRAPE=1 but proxy_configured=false — set PROXY_URL"
    fi
  fi
else
  ko "GET /v1/health" "unreachable or status!=ok — run: docker compose up -d"
fi

gate=$(curl -sf "$API/v1/product-gate" 2>/dev/null || true)
if echo "$gate" | grep -q '"pass":true'; then
  ok "GET /v1/product-gate"
else
  ko "GET /v1/product-gate" 'pass!=true — run: docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile publish'
fi

budgets=$(curl -sf "$API/v1/budgets/totals" 2>/dev/null || true)
if echo "$budgets" | grep -q '"lines"'; then
  lines=$(echo "$budgets" | python3 -c "import json,sys; print(json.load(sys.stdin).get('lines',0))" 2>/dev/null || echo 0)
  if [[ "${lines:-0}" -gt 0 ]]; then
    ok "GET /v1/budgets/totals (lines=${lines})"
  else
    ko "GET /v1/budgets/totals" "lines=0 — seed history or presupuesto_corpus"
  fi
else
  ko "GET /v1/budgets/totals" "missing lines field — seed history profile"
fi

echo "----"
echo "Passed: $PASS  Failed: $FAIL"
if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
exit 0
