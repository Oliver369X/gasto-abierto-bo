# Staging go / no-go — Gasto Abierto

Checklist operativo antes de promover a producción o abrir tráfico externo. Completar en orden; cualquier ítem **NO-GO** bloquea el deploy.

**Automatizado (HTTP smoke):** con el stack arriba y seeds aplicados (§3):

```bash
make staging-check
# equivalente: bash scripts/staging_check.sh
# API custom: STAGING_API_URL=https://api.staging.ejemplo.bo make staging-check
```

Verifica `GET /v1/health`, `GET /v1/product-gate` (`pass: true`), `GET /v1/budgets/totals` (`lines > 0`). Si `LIVE_SCRAPE=1` en `.env`, exige `proxy_configured: true` en health.

Despliegue VPS / producción: [`vps-deploy.md`](vps-deploy.md) y [`.env.production.example`](../../.env.production.example).

## 1. Infraestructura

| # | Check | Comando / evidencia | GO |
|---|-------|---------------------|-----|
| 1.1 | Stack healthy | `docker compose ps` — api, web, db, cache `healthy` | ☐ |
| 1.2 | Puertos sin conflicto (Opportunity u otros) | `.env`: host ports (`API_HOST_PORT`, `WEB_HOST_PORT`, etc.) distintos del otro stack | ☐ | <!-- pragma: allowlist secret -->
| 1.3 | Migraciones aplicadas | `GET /v1/health` → `db.ok: true` | ☐ |
| 1.4 | Proxy configurado para live | `GET /v1/health` → `proxy.proxy_configured: true` si `LIVE_SCRAPE=1` | ☐ |
| 1.5 | Sin secretos en git | `.env` local only; credenciales en vault/CI secrets | ☐ |
| 1.6 | API bind configurable | `API_HOST` / `API_PORT` en entrypoint (host network) | ☐ |
| 1.7 | LIVE sin proxy bloqueado | `LIVE_SCRAPE=1` sin `PROXY_URL` → api/worker **no arrancan** | ☐ |
| 1.8 | URLs públicas de staging | `NEXT_PUBLIC_API_URL`, `CORS_ORIGINS` apuntan al dominio staging | ☐ |

## 2. Datos offline (smoke obligatorio)

| # | Check | Comando | GO |
|---|-------|---------|-----|
| 2.1 | Contract tests | `pytest tests/contract tests/test_common.py -q` | ☐ |
| 2.2 | MEFP geo ≥100 ubicaciones | `pytest tests/test_mefp_geo.py -q` | ☐ |
| 2.3 | SICOES offline | `pytest tests/test_sicoes_resilience.py -q` | ☐ |
| 2.4 | Presupuesto corpus | `pytest tests/test_fetch_presupuesto.py -q` | ☐ |
| 2.5 | MVP verify | `bash scripts/verify_mvp.sh` (S1–S16) | ☐ |
| 2.6 | Staging HTTP smoke | `make staging-check` | ☐ |

## 3. Seeds staging

Ejecutar tras `docker compose up -d`:

```bash
# Demo mínimo (boot default)
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile demo

# Histórico multi-año (presupuesto + contratos alineados)
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile history

# Presupuesto offline cuando PRESUPUESTO_ABIERTO_DOWNLOAD_URLS vacío
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile presupuesto_corpus

# Product-gate G10 + incendios demo
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile publish
```

| # | Check | Evidencia | GO |
|---|-------|-----------|-----|
| 3.1 | Entidades | `GET /v1/entities` no vacío | ☐ |
| 3.2 | Presupuesto | `GET /v1/budgets/totals` → `lines > 0` | ☐ |
| 3.3 | Histórico | `GET /v1/history/years` multi-año | ☐ |
| 3.4 | Product gate | `GET /v1/product-gate` → `"pass": true` | ☐ |
| 3.5 | Fire demo | `gasto seed --profile fire_demo` idempotente; ledger 870k verificable | ☐ |

## 4. Live refresh (opcional pre-prod)

Solo con proxy; no en CI.

```bash
# Presupuesto oficial
python -m scripts.cli gasto fetch-presupuesto --list-only
LIVE_SCRAPE=1 PROXY_URL=http://host.docker.internal:7890 \
  python -m scripts.cli gasto fetch-presupuesto --force

# SICOES
LIVE_SCRAPE=1 PROXY_URL=... \
  docker compose run --rm worker python -m scripts.cli gasto ingest --source sicoes --sync --live
```

| # | Check | GO |
|---|-------|-----|
| 4.1 | Descarga presupuesto escribe manifest + archivos >100 B | ☐ |
| 4.2 | Ingesta live no deja DB en estado parcial sin rollback manual documentado | ☐ |

## 5. Diferido explícito (NO bloquea staging demo)

Ver `docs/wave4-deferred.md`: auth prod, cliente TS, charts, FIRMS live map, Excel/Drive, MEFP 352 completo (fuente: `docs/sources/mefp_ubicaciones.md`).

## Decisión

| Rol | Nombre | Fecha | GO / NO-GO |
|-----|--------|-------|------------|
| Ops | | | |
| Product | | | |

**Criterio GO:** todos los ítems §1–§3 marcados; §4 solo si staging incluye refresh live. `make staging-check` debe pasar tras `publish` seed.
