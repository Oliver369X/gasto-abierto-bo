# Architecture — Gasto Abierto Bolivia (MVP)

## Goals

Unify public spending data from Bolivian official sources into a versioned historical store, expose a public read API, and surface explainable risk alerts for citizens.

## Components

| Component | Role |
|-----------|------|
| `services/api` | FastAPI read API `/v1/*` (routers under `api/routers/`) |
| `services/worker` | ARQ jobs + SourceAdapters + persist |
| `services/web` | Next.js citizen UI |
| `packages/schema` | SQLAlchemy models + Alembic |
| `packages/common` | parsers, fire helpers (`common.fire.*`), fuzzy match, jobs |
| PostgreSQL | canonical + SCD2 history |
| Redis | ARQ queue + stats cache |
| MinIO | raw object lake |

## CLI → worker → packages

Ingest and fire pipelines follow a thin CLI → worker → packages layout:

1. **CLI** (`python -m scripts.cli gasto|fire`): parse flags, set env, call worker entrypoints. See `docs/runbook-cli.md`.
2. **Worker** (`services/worker/`): orchestration, DB sessions, adapters, persist jobs.
3. **Packages** (`packages.common`, `packages.schema`): pure helpers and models — no I/O side effects beyond what callers pass in.

Example: `common.fire.classify` / `ledger` / `rollup` are imported by the API and worker; shims under `common.fire_*` are removed.

## Data flow

1. Scheduler / CLI encola `JobEnvelope` o corre `scripts/ingest.py --sync`.
2. Adapter `discover` → `fetch` (bytes a MinIO + fila `document`) → `parse` → staging.
3. Normalizer resuelve entidades/proveedores (NIT > fuzzy aliases); presupuestos usan SCD2.
4. Upsert histórico; cruce CUCE inter-fuentes → `discrepancy`.
5. Alert rules materializan filas con explicación en español y nombres legibles.
6. API sirve lectura; UI muestra dashboard, búsqueda, auditorías, fuentes y drill-down.

## SourceAdapter contract

Every source is a plugin. CI never requires live network: parsers run against committed fixtures.

## Scaling path (not in MVP)

- Replace ARQ with Kafka consumers using the same `JobEnvelope`.
- Replace cron with Airflow DAGs calling the same adapters.
- Add Elasticsearch index for full-text supplier/contract search.
