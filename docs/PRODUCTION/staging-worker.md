# Worker en staging — perfiles y límites de memoria

Guía para el worker ARQ en **staging VPS** antes del go-live público. Complementa [`vps-deploy.md`](vps-deploy.md) y [`staging-go-no-go.md`](staging-go-no-go.md).

## Perfiles de carga

| Perfil | Cuándo | Servicios | RAM worker sugerida |
|--------|--------|-----------|---------------------|
| **demo** | Smoke post-deploy | `demo` seed, cron deshabilitado manualmente | 512 MiB |
| **staging** | Pre go-live (recomendado) | `history` + `presupuesto_corpus` + `fire_demo` + `harden` | 1–2 GiB |
| **publish** | Product-gate G10 completo | `publish` + deep corpus | 1–2 GiB |
| **live-ingest** | Refresh semanal | `presupuesto_abierto` parquet + SICOES live | 2–4 GiB |

El parseo de Parquet de Presupuesto Abierto y los jobs ARQ concurrentes son los principales consumidores de RAM.

## Compose staging (límites de memoria)

Usar el overlay opcional [`compose.staging.yml`](../../compose.staging.yml):

```bash
docker compose -f docker-compose.yml -f compose.staging.yml up -d --build
```

Variables en `.env`:

```env
WORKER_MEMORY_LIMIT=2g
WORKER_MEMORY_RESERVATION=512m
API_MEMORY_LIMIT=1g
ARQ_MAX_JOBS=2
```

### Qué hace el overlay

- **worker**: `deploy.resources.limits.memory` (default 2g) y `ARQ_MAX_JOBS=2` para evitar picos de ingest paralelos.
- **api**: límite 1g (suficiente para lecturas públicas + product-gate).

En Docker Compose v2 sin Swarm, `deploy.resources` se aplica en modo **standalone** desde Compose v2.23+; si tu host no lo soporta, fijá límites con `docker update --memory=2g gasto-abierto-worker-1` tras el primer `up`.

## Seeds recomendados en staging

Orden (mismo que go-live, sin tráfico externo):

```bash
# Un comando (recomendado):
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile staging
make staging-check

# Alternativa granular:
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile demo
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile history
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile presupuesto_corpus
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile publish
make staging-check
```

## LIVE_SCRAPE en staging

Solo con proxy configurado (`PROXY_URL`). El worker **no arranca** si `LIVE_SCRAPE=1` sin proxy (fail loud).

```bash
curl -s "$STAGING_API_URL/v1/health" | jq .proxy
```

## Verificación

```bash
make staging-check
make go-live-check   # tras URLs públicas + PRESUPUESTO_ABIERTO_DOWNLOAD_URLS en .env
```

Ver checklist completo: [`go-live.md`](go-live.md).
