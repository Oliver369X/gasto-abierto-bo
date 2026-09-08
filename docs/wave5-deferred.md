# Wave 5 — diferido explícito

| Prioridad | Ítem | Estado |
|-----------|------|--------|
| P0 | `API_HOST` / `API_PORT` en entrypoint (host network) | Hecho |
| P0 | `make staging-check` + `scripts/staging_check.sh` | Hecho |
| P0 | Fail loud `LIVE_SCRAPE=1` sin `PROXY_URL` (api + worker startup) | Hecho |
| P1 | `.env.production.example` + `docs/PRODUCTION/vps-deploy.md` | Hecho |
| P1 | MEFP 117 → 166 ubicaciones + `docs/sources/mefp_ubicaciones.md` | Hecho |
| P2 | `fire_demo` / `publish` tests en CI (`test_fire_demo_argv.py`) | Hecho (wave 4) |

## Sigue diferido (no bloquea staging)

| Ítem | Próximo paso |
|------|----------------|
| Auth producción | OIDC / API keys |
| Cliente TS generado | OpenAPI codegen |
| Charts dashboard | Recharts / viz |
| FIRMS mapa live | MapLibre + tiles |
| MEFP 352 completo | Merge GeoPackage oficial — ver `docs/sources/mefp_ubicaciones.md` |
| Excel / Google Drive | Fuera de alcance |

## Verificación rápida

```bash
make test
make staging-check   # requiere stack + publish seed
bash scripts/verify_mvp.sh
```
