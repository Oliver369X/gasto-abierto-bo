.PHONY: staging-check go-live-check verify test

# Staging HTTP smoke (API must be up; seeds per docs/PRODUCTION/staging-go-no-go.md)
staging-check:
	bash scripts/staging_check.sh

# Production go-live gate (public URLs, proxy, presupuesto env, product-gate, budgets)
# Usage (GNU make): make go-live-check -- --allow-demo-urls
go-live-check:
	bash scripts/go_live_check.sh $(filter-out go-live-check,$(MAKECMDGOALS))

%:
	@:

# Full MVP verify (offline tests + API if reachable)
verify:
	bash scripts/verify_mvp.sh

# Offline unit/contract tests (no Docker)
test:
	PYTHONPATH=packages:services pytest tests/contract tests/test_common.py tests/test_mefp_geo.py tests/test_proxy.py tests/test_env_validate.py tests/test_go_live_check.py tests/test_web_download_urls.py tests/test_fire_demo_argv.py tests/test_staging_seed.py -q
