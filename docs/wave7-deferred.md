# Wave 7 — MEFP 280+, staging seed, go-live ES

| Prioridad | Ítem | Estado |
|-----------|------|--------|
| P0 | Profile `staging` = history + presupuesto_corpus + fire_demo + harden | Hecho |
| P0 | `docs/PRODUCTION/merge-order.md` (wave2→wave7, squash sequence) | Hecho |
| P1 | MEFP 224 → **280** ubicaciones + tests ≥280; gap 72 a GeoPackage | Hecho |
| P1 | `go-live-check` mensajes en español + `--allow-demo-urls` | Hecho |
| P1 | `go-live.md` checklist Diego actualizado | Hecho |
| P1 | CI: go_live + mefp + web download URL tests explícitos | Hecho |

## Sigue diferido — solo P2 real

| Ítem | Próximo paso |
|------|----------------|
| MEFP 352 completo | Merge GeoPackage oficial (72 ubicaciones restantes) — `docs/sources/mefp_ubicaciones.md` |
| Auth producción | OIDC / API keys — `AUDIT.md` |
| Cliente TypeScript | OpenAPI codegen |
| Charts dashboard | Recharts / viz histórico |
| FIRMS mapa live | MapLibre + tiles + `MAP_KEY` |
| Excel / Google Drive | Fuera de alcance (política de datos) |

## Verificación rápida

```bash
make test
pytest tests/test_go_live_check.py tests/test_mefp_geo.py tests/test_web_download_urls.py tests/test_staging_seed.py -q
python -m scripts.cli gasto seed --profile staging   # tras compose up
make staging-check
make go-live-check --allow-demo-urls   # solo caja local
```

Wave 6 cerrado en [`wave6-deferred.md`](wave6-deferred.md). Merge order: [`docs/PRODUCTION/merge-order.md`](PRODUCTION/merge-order.md).
