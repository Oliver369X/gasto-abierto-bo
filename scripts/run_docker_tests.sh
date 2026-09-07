#!/bin/sh
set -e
echo "== unit/contract (offline) =="
pytest tests/contract tests/test_common.py tests/test_api_smoke.py tests/test_alerts.py tests/test_storage.py tests/test_proxy.py tests/test_history_fixture.py tests/test_pipeline_resilience.py tests/test_categorize.py tests/test_discrepancy_delta.py tests/test_cuce.py tests/test_cross_source.py -q --tb=short
python -m scripts.cli gasto seed --profile cross || true
echo "== seed history =="
python -m scripts.cli gasto seed --profile history
echo "== generate + seed deep corpus =="
python scripts/_legacy/generate_deep_corpus.py
python -m scripts.cli gasto seed --profile deep
echo "== wait for API =="
i=0
until python -c "import httpx,os; u=os.getenv('API_INTERNAL_URL','http://api:8000'); httpx.get(u+'/v1/health',timeout=3).raise_for_status()" 2>/dev/null; do
  i=$((i+1))
  if [ "$i" -gt 40 ]; then echo "API not healthy"; exit 1; fi
  sleep 2
done
echo "== API history + cross-source check =="
python scripts/_legacy/check_history_api.py
python scripts/_legacy/check_deep_api.py
echo "ALL DOCKER TESTS PASSED"
