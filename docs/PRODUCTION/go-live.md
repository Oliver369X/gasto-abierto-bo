# Go-live — Gasto Abierto (Diego)

One-pager operativo para abrir tráfico público. Base branch: `main` ← merge desde staging validado. Orden de olas: [`merge-order.md`](merge-order.md).

## Checklist Diego (orden exacto)

| # | Paso | Comando / acción | GO |
|---|------|------------------|-----|
| 1 | **Merge código** | Squash-merge PR Wave 6 → Wave 7 a `main` (ver [`merge-order.md`](merge-order.md)) | ☐ |
| 2 | **Infra VPS** | Docker Compose + TLS (reverse proxy → `WEB_HOST_PORT` / `API_HOST_PORT`) | ☐ | <!-- pragma: allowlist secret -->
| 3 | **Env producción** | Copiar [`.env.production.example`](../../.env.production.example) → `.env` en servidor (vault para DB/passwords) | ☐ |
| 4 | **Stack** | `docker compose -f docker-compose.yml -f compose.staging.yml up -d --build` (ver [`staging-worker.md`](staging-worker.md)) | ☐ |
| 5 | **Seed staging** | `docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile staging` | ☐ |
| 6 | **Staging check** | `make staging-check` (HTTP smoke interno) | ☐ |
| 7 | **Go-live check** | `make go-live-check` (URLs públicas + presupuesto + product-gate) | ☐ |
| 8 | **DNS / TLS** | Apuntar dominios; reconstruir `web` si cambia `NEXT_PUBLIC_API_URL` | ☐ |
| 9 | **Abrir tráfico** | Solo si pasos 6 y 7 OK | ☐ |

**Caja local (no prod):** `make go-live-check -- --allow-demo-urls` (GNU make) permite hosts de ejemplo (`api.gasto.ejemplo.bo`).

## Variables críticas (`.env`)

| Variable | Producción |
|----------|------------|
| `NEXT_PUBLIC_API_URL` | `https://api.tudominio.bo` (nunca loopback / [REDACTED]) |  <!-- pragma: allowlist secret -->
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

## Seeds

### Staging (recomendado — un comando)

Tras `docker compose up -d`:

```bash
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile staging
```

Ejecuta en orden: `history` → `presupuesto_corpus` → `fire_demo` → `harden`.

### Perfiles individuales (alternativa)

```bash
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile demo
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile history
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile presupuesto_corpus
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile publish
```

`publish` incluye deep corpus + G10; `staging` es más ligero para VPS staging.

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
# Caja local (GNU make): make go-live-check -- --allow-demo-urls
```

**Validación env (Python):** el paso env ejecuta `python -m common.go_live_validate`. En el host hace falta `pip install -e ".[dev]"` (importa `rapidfuzz` vía `common/__init__.py`). Si el host no tiene deps, el script reintenta en el contenedor `api` cuando está corriendo; alternativa manual:

```bash
docker compose exec -T api python -m common.go_live_validate
```

**Falla si:**

- `NEXT_PUBLIC_API_URL` apunta a loopback ([REDACTED] / [REDACTED]) sin `--allow-demo-urls`  <!-- pragma: allowlist secret -->
- `LIVE_SCRAPE=1` sin proxy configurado
- `PRESUPUESTO_ABIERTO_DOWNLOAD_URLS` (y legacy `PRESUPUESTO_ABIERTO_URLS`) vacíos
- `GET /v1/product-gate` → `pass != true`
- `GET /v1/budgets/totals` → `lines == 0`

Mensajes de error en español en consola. Checklist manual ampliado: [`staging-go-no-go.md`](staging-go-no-go.md).

## Rollback rápido

1. Reverse proxy → página estática / mantenimiento.
2. `docker compose pull && docker compose up -d` con tag anterior.
3. DB: restore snapshot pre-seed si seeds corruptos (ver `docs/ops.md` backup).

## Diferido (no bloquea go-live demo)

Solo P2 real — ver [`docs/wave7-deferred.md`](../wave7-deferred.md) y [`docs/wave6-deferred.md`](../wave6-deferred.md).
