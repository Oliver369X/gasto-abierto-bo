# Wave 6 — cierre blockers lanzamiento público

| Prioridad | Ítem | Estado |
|-----------|------|--------|
| P0 | `make go-live-check` (URLs, proxy, presupuesto env, product-gate, budgets) | Hecho |
| P0 | Web: sin loopback en enlaces CSV/descarga + test regresión | Hecho |  # pragma: allowlist secret
| P1 | MEFP 166 → 224 ubicaciones + tests ≥200 | Hecho |
| P1 | `docs/PRODUCTION/go-live.md` one-pager Diego | Hecho |
| P1 | Worker staging: `staging-worker.md` + `compose.staging.yml` | Hecho |
| P1 | `make staging-check` (wave 5) | Hecho |

## Sigue diferido — solo P2 real (no bloquea go-live demo)

| Ítem | Próximo paso |
|------|----------------|
| Auth producción | OIDC / API keys — `AUDIT.md` |
| Cliente TypeScript | OpenAPI codegen |
| Charts dashboard | Recharts / viz histórico |
| FIRMS mapa live | MapLibre + tiles + `MAP_KEY` |
| MEFP 352 completo | Merge GeoPackage oficial — `docs/sources/mefp_ubicaciones.md` |
| Excel / Google Drive | Fuera de alcance (política de datos) |

## Verificación rápida

```bash
make test
pytest tests/test_go_live_check.py tests/test_web_download_urls.py tests/test_mefp_geo.py -q
make staging-check    # stack + publish seed
make go-live-check    # .env producción + mismos seeds
```

Wave 5 cerrado en [`wave5-deferred.md`](wave5-deferred.md). Wave 4 en [`wave4-deferred.md`](wave4-deferred.md).
