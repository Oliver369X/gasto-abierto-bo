.PHONY: staging-check verify test

# Staging HTTP smoke (API must be up; seeds per docs/PRODUCTION/staging-go-no-go.md)
staging-check:
	bash scripts/staging_check.sh

# Full MVP verify (offline tests + API if reachable)
verify:
	bash scripts/verify_mvp.sh

# Offline unit/contract tests (no Docker)
test:
	PYTHONPATH=packages:services pytest tests/contract tests/test_common.py tests/test_mefp_geo.py tests/test_proxy.py tests/test_env_validate.py tests/test_fire_demo_argv.py -q
