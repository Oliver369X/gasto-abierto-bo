#!/usr/bin/env bash
# Go-live readiness: public URLs, proxy, presupuesto env, product-gate, budgets.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source "$ROOT/scripts/_lib/loopback_host.sh"

ALLOW_DEMO=0
EXTRA_PY_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --allow-demo-urls)
      ALLOW_DEMO=1
      EXTRA_PY_ARGS+=(--allow-demo-urls)
      shift
      ;;
    -h|--help)
      echo "Uso: $0 [--allow-demo-urls]"
      echo "  --allow-demo-urls  Permite URLs de ejemplo en caja local (no usar en prod)"
      exit 0
      ;;
    *)
      echo "Opción desconocida: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  set -a
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]] && export "$line"
  done < .env
  set +a
fi

API_HOST_PORT="${API_HOST_PORT:-8010}"
API="${GO_LIVE_API_URL:-${STAGING_API_URL:-${API_URL:-http://${_LOCAL_HOST}:${API_HOST_PORT}}}}"

PASS=0
FAIL=0
ok() { echo "OK  $1"; PASS=$((PASS + 1)); }
ko() { echo "FAIL $1 — $2"; FAIL=$((FAIL + 1)); }

run_env_validate() {
  if PYTHONPATH=packages:services python3 -m common.go_live_validate "${EXTRA_PY_ARGS[@]}"; then
    return 0
  fi
  if command -v docker >/dev/null 2>&1 \
    && docker compose ps api --status running -q 2>/dev/null | grep -q .; then
    echo "Reintentando validación env en contenedor api (host sin deps del proyecto)..." >&2
    docker compose exec -T api python -m common.go_live_validate "${EXTRA_PY_ARGS[@]}"
    return $?
  fi
  return 1
}

echo "Go-live check → env + $API"
if [[ "$ALLOW_DEMO" -eq 1 ]]; then
  echo "(modo local: --allow-demo-urls activo)"
fi

if run_env_validate; then
  ok "env (NEXT_PUBLIC_API_URL, LIVE_SCRAPE/proxy, PRESUPUESTO URLs)"
else
  ko "env" "revisá los errores arriba — corregí .env o usá contenedor api (pip install -e .[dev])"
fi

health=$(curl -sf "$API/v1/health" 2>/dev/null || true)
if echo "$health" | grep -q '"status":"ok"'; then
  ok "GET /v1/health"
  if [[ "${LIVE_SCRAPE:-0}" == "1" ]]; then
    if echo "$health" | grep -q '"proxy_configured":true'; then
      ok "proxy (LIVE_SCRAPE=1)"
    else
      ko "proxy" "LIVE_SCRAPE=1 pero proxy_configured=false — configurá PROXY_URL"
    fi
  fi
else
  ko "GET /v1/health" "API inalcanzable o status!=ok — ¿stack arriba?"
fi

gate=$(curl -sf "$API/v1/product-gate" 2>/dev/null || true)
if echo "$gate" | grep -q '"pass":true'; then
  ok "GET /v1/product-gate"
else
  ko "GET /v1/product-gate" 'pass!=true — ejecutá: gasto seed --profile staging (o publish)'
fi

budgets=$(curl -sf "$API/v1/budgets/totals" 2>/dev/null || true)
if echo "$budgets" | grep -q '"lines"'; then
  lines=$(echo "$budgets" | python3 -c "import json,sys; print(json.load(sys.stdin).get('lines',0))" 2>/dev/null || echo 0)
  if [[ "${lines:-0}" -gt 0 ]]; then
    ok "GET /v1/budgets/totals (lines=${lines})"
  else
    ko "GET /v1/budgets/totals" "lines=0 — ejecutá: gasto seed --profile staging (o history)"
  fi
else
  ko "GET /v1/budgets/totals" "campo lines ausente o respuesta inválida"
fi

echo "----"
echo "Passed: $PASS  Failed: $FAIL"
if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
exit 0
