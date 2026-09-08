# Go-live — Gasto Abierto (Diego)

One-pager operativo para abrir tráfico público. Base branch: `main` ← merge desde staging validado.

## Orden de merge / deploy

1. **Código** — merge PR Wave 6 (staging-readiness + blockers) a `main`.
2. **Infra** — VPS con Docker Compose + TLS (reverse proxy → `WEB_HOST_PORT` / `API_HOST_PORT`).  # pragma: allowlist secret
3. **Env** — copiar [`.env.production.example`](../../.env.production.example) → `.env` en servidor (vault para DB/passwords).
4. **Stack** — `docker compose -f docker-compose.yml -f compose.staging.yml up -d --build` (ver [`staging-worker.md`](staging-worker.md)).
5. **Seeds** — perfiles en orden (§ Seeds abajo).
6. **Staging check** — `make staging-check` (HTTP smoke interno).
7. **Go-live check** — `make go-live-check` (URLs públicas + presupuesto + product-gate).
8. **DNS / TLS** — apuntar dominios; reconstruir `web` si cambia `NEXT_PUBLIC_API_URL`.
9. **Abrir tráfico** — solo si ambos checks pasan.

## Variables críticas (`.env`)

| Variable | Producción |
|----------|------------|
| `NEXT_PUBLIC_API_URL` | `https://api.tudominio.bo` (nunca loopback / localhost) |  # pragma: allowlist secret
| `CORS_ORIGINS` | `https://tudominio.bo` |
| `PRESUPUESTO_ABIERTO_DOWNLOAD_URLS` | URL Parquet oficial (ver README) |
| `LIVE_SCRAPE` | `0` al abrir; `1` solo con `PROXY_URL` |
| `PROXY_URL` | Obligatorio si `LIVE_SCRAPE=1` |
| `STRICT_PRODUCTION_ENV` | `1` recomendado (api/worker rechazan loopback) |

Ejemplo presupuesto:

```env
PRESUPUESTO_ABIERTO_DOWNLOAD_URLS=https://abierto.economiayfinanzas.gob.bo/presupuesto/descargas/gasto/ultimo/gasto.parquet
```

Sin secretos en git. Sin Excel / Google Drive.

## Seeds (publish)

Tras `docker compose up -d`:

```bash
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile demo
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile history
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile presupuesto_corpus
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile publish
```

`publish` habilita **product-gate G10** e incendios demo. No usar `BOOT_PUBLISH_SEED=1` en prod salvo bootstrap controlado.

## Checks automatizados

### Staging (pre-promoción)

```bash
make staging-check
# API custom: STAGING_API_URL=https://api.staging.ejemplo.bo make staging-check
```

Verifica: `/v1/health`, `/v1/product-gate` (`pass: true`), `/v1/budgets/totals` (`lines > 0`), proxy si `LIVE_SCRAPE=1`.

### Go-live (apertura pública)

```bash
make go-live-check
# API custom: GO_LIVE_API_URL=https://api.tudominio.bo make go-live-check
```

**Falla si:**

- `NEXT_PUBLIC_API_URL` apunta a loopback (localhost / 127.0.0.1)  # pragma: allowlist secret
- `LIVE_SCRAPE=1` sin proxy configurado
- `PRESUPUESTO_ABIERTO_DOWNLOAD_URLS` (y legacy `PRESUPUESTO_ABIERTO_URLS`) vacíos
- `GET /v1/product-gate` → `pass != true`
- `GET /v1/budgets/totals` → `lines == 0`

Checklist manual ampliado: [`staging-go-no-go.md`](staging-go-no-go.md).

## Rollback rápido

1. Reverse proxy → página estática / mantenimiento.
2. `docker compose pull && docker compose up -d` con tag anterior.
3. DB: restore snapshot pre-seed si seeds corruptos (ver `docs/ops.md` backup).

## Diferido (no bloquea go-live demo)

Solo P2 real — ver [`docs/wave6-deferred.md`](../wave6-deferred.md).
