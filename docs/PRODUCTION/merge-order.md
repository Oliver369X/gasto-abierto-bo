# Merge order — Gasto Abierto (Wave 2 → Wave 7)

Guía para Diego y el equipo: orden recomendado de integración a `main`, tips por ola y notas de release. Las olas 2–5 ya están en la línea de commits de la rama de trabajo; Wave 6/7 llegan como PRs desde `cursor/wave*-…`.

## Secuencia recomendada (squash merge → `main`)

| # | Ola | Commit / rama tip | Qué trae | Merge a `main` |
|---|-----|-------------------|----------|----------------|
| 1 | **Wave 2** | `68f92a5` | Presupuesto live + proxy gate, cron SICOES, fire CI, MEFP 27 ubicaciones, UI banners | Base histórica (ya en rama) |
| 2 | **Wave 3** | `d2fec5b` | MEFP 60, `fire_demo_impl`, fixtures histórico, SICOES resilience, `wave3-deferred.md` | Tras Wave 2 |
| 3 | **Wave 4** | `b19a26b` | MEFP 117, `presupuesto_corpus`, puertos compose, `staging-go-no-go.md` | Tras Wave 3 |
| 4 | **Wave 5** | `4751f27` | `staging-check`, `.env.production.example`, MEFP 166, fail loud sin proxy | Tras Wave 4 |
| 5 | **Wave 6** | `cursor/wave6-public-launch-blockers-0425` | `go-live-check`, MEFP 224, `compose.staging.yml`, web download URLs, `go-live.md` | **PR → squash → main** |
| 6 | **Wave 7** | `cursor/wave7-mefp-staging-golive-44ce` | MEFP 280+, profile `staging`, merge-order, go-live ES, CI gates | **PR → squash → main** (tras Wave 6) |

**Regla:** no saltar olas — cada wave asume seeds, docs y tests de la anterior.

## Tips por rama / PR

### Wave 6 (`cursor/wave6-public-launch-blockers-0425`)

- Bloqueadores de lanzamiento público: `make go-live-check`, enlaces web sin loopback.
- Revisar diff en `services/web/` (CSV/descargas) y `packages/common/go_live_validate.py`.
- Tras merge: tag opcional `v0.6-staging-ready`.

### Wave 7 (`cursor/wave7-mefp-staging-golive-44ce`)

- Profile único staging: `gasto seed --profile staging` (history + corpus + fire + harden).
- MEFP 280/352 — gap 72 documentado en `docs/sources/mefp_ubicaciones.md`.
- `make go-live-check --allow-demo-urls` solo en caja local.

## Release notes (plantilla por ola)

```markdown
## Gasto Abierto — Wave N

### Added
- …

### Changed
- …

### Ops (Diego)
1. git pull && docker compose -f docker-compose.yml -f compose.staging.yml up -d --build
2. cp .env.production.example .env  # vault para secretos
3. docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile staging
4. make staging-check
5. (pre-apertura) make go-live-check

### Deferred
- Ver docs/waveN-deferred.md
```

## Post-merge smoke (obligatorio)

```bash
make test
pytest tests/test_go_live_check.py tests/test_mefp_geo.py tests/test_web_download_urls.py -q
make staging-check    # stack + seed staging
make go-live-check    # .env producción
```

## Diferido global (no bloquea merge)

Auth prod, cliente TS, charts, mapa FIRMS live, MEFP 352 completo (GeoPackage), Excel/Drive — ver `docs/wave6-deferred.md` y `docs/wave7-deferred.md`.
