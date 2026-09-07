# Runbook CLI — Gasto Abierto BO

Camino oficial (no usar `scripts/f5_*.py` ni monolitos en root salvo `_legacy/`).

```bash
export PYTHONPATH=packages:services:.
# o desde contenedor api/worker con PYTHONPATH ya seteado
python -m scripts.cli --help
```

## Gasto

| Comando | Ejemplo |
|---------|---------|
| Ingest sync | `python -m scripts.cli gasto ingest --source sicoes --sync` |
| Ingest live | `LIVE_SCRAPE=1 python -m scripts.cli gasto ingest --source sicoes --sync --live` |
| Enqueue | `python -m scripts.cli gasto ingest --all --enqueue` |
| Seed | `python -m scripts.cli gasto seed --profile demo` |
| Profiles | `demo` \| `history` \| `deep` \| `cross` \| `real` |
| Harden | `python -m scripts.cli gasto harden` |
| Verify | `python -m scripts.cli gasto verify` |
| Open data | `python -m scripts.cli gasto fetch-open-data [--force] [--list-only]` |
| Enrich dry | `python -m scripts.cli gasto enrich-sicoes --limit 100 --year-from 2024 --dry-run` |
| Enrich live | `PROXY_URL=... LIVE_SCRAPE=1 python -m scripts.cli gasto enrich-sicoes --limit 5000 --year-from 2024` |
| Stats cache | `python -m scripts.cli gasto refresh-stats` |
| RAW sample | `python -m scripts.cli gasto raw-backfill --limit 50` |

Destino open-data: `tests/fixtures/real/`.

## Fire (AURA Incendios)

| Comando | Ejemplo |
|---------|---------|
| Fase | `python -m scripts.cli fire pipeline --phase f1` |
| Alias | `python -m scripts.cli fire run --phase all` |
| Verify | `python -m scripts.cli fire verify` |

Wrappers PowerShell:

```powershell
powershell -File .\scripts\run_fire_pipeline.ps1
powershell -File .\scripts\verify_fire_plan2.ps1
```

## Legacy

Código movido a `scripts/_legacy/` — **no usar en CI/prod**. Ver README ahí.
