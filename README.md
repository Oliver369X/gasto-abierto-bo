# Gasto Abierto Bolivia

Plataforma ciudadana **open source** para fiscalizar el gasto público boliviano a partir de fuentes oficiales dispersas (Presupuesto Abierto, SICOES, datos.gob.bo, Contraloría, portales de Santa Cruz).

> Capa ciudadana tipo [Dozorro](https://dozorro.org/): consolidar, versionar, alertar y explicar — siempre con enlace a la fuente primaria.

## Quickstart

```bash
cp .env.example .env
docker compose up -d --build
# esperar ~60s a healthchecks
./scripts/verify_mvp.sh   # o: powershell -File scripts/verify_mvp.ps1
```

### Comandos oficiales (CLI)

Camino único — ver [`docs/runbook-cli.md`](docs/runbook-cli.md):

```bash
python -m scripts.cli --help
python -m scripts.cli gasto seed --profile demo
python -m scripts.cli gasto verify
python -m scripts.cli gasto ingest --source sicoes --sync
python -m scripts.cli fire pipeline --phase f1
python -m scripts.cli fire verify
```

No usar wrappers sueltos `scripts/f5_*.py` ni `seed_fire_2024.py` (están en `scripts/_legacy/` o eliminados).

| Servicio | URL |
|----------|-----|
| API OpenAPI | http://localhost:8010/docs |
| Dashboard | http://localhost:3010 |
| MinIO console | http://localhost:9011 |
| Postgres (host) | localhost:5434 |

### Tests (Docker obligatorio para verificación)

```powershell
# Entorno local de edición (solo .venv — nunca pip al sistema)
powershell -File .\scripts\setup_venv.ps1
.\.venv\Scripts\Activate.ps1

# Verificación de producto (Docker)
.\scripts\test_docker.ps1
```

Incluye pytest offline + seed histórico 2019–2025 + check `/v1/history/years`.

### Histórico + proxy

```bash
# Serie multi-año (offline, sin red)
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile history

# Histórico SICOES TODAS las gestiones (2007→hoy) — script masivo en _legacy o:
# docker compose run … python scripts/_legacy/seed_all_years.py

# Live scrape: SIEMPRE con VPN/proxy (ver docs/ops.md)
LIVE_SCRAPE=1 docker compose run --rm worker python -m scripts.cli gasto ingest --source sicoes --sync --live
```

UI histórico: http://localhost:3010/historico  
Cruce: `GET http://localhost:8010/v1/cross-source/summary`

## Arquitectura (MVP lean)

- **Python / FastAPI** — API pública de lectura
- **PostgreSQL** — histórico con SCD2 + provenance
- **Redis + ARQ** — cola de jobs de ingesta
- **MinIO** — data lake de raw (HTML/PDF/CSV)
- **Playwright** — scrapers de sitios dinámicos
- **Next.js** — UI ciudadana en español

Kafka / Airflow / Elasticsearch / Kubernetes: documentados para Fase 2 (`docs/roadmap.md`), no desplegados en MVP.

## Fuentes MVP

| Fuente | Adapter | Notas |
|--------|---------|-------|
| datos.gob.bo (CKAN) | `agetic` | Bootstrap OCDS / datasets |
| SICOES | `sicoes` | HTML vivo, rate ≤1 rps |
| Presupuesto Abierto | `presupuesto_abierto` | XHR/JSON del portal |
| Contraloría (informes) | `cge` | Solo metadatos públicos |
| GAD / GAM Santa Cruz | `gad_scz`, `gam_scz` | HTML + PDF texto |
| Ministerio de Defensa (RPC) | `mindef` | Vertical AURA Incendios |
| ABT (ejecución) | `abt` | Prevención / bosques |

## AURA Incendios

Vertical de **libro mayor** del gasto en incendios forestales (no una sola cifra oficial consolidada).

```powershell
# Stack
docker compose up -d --build postgres redis minio api web

# CLI (preferido)
python -m scripts.cli fire verify
python -m scripts.cli fire pipeline --phase f1

# Wrappers Docker (llaman al CLI)
powershell -File .\scripts\verify_fire_plan2.ps1
powershell -File .\scripts\run_fire_pipeline.ps1
```

Documentación operativa / prod: [`docs/aura-incendios/DOCKER.md`](docs/aura-incendios/DOCKER.md) · gates: [`docs/aura-incendios/gates.md`](docs/aura-incendios/gates.md)

| Recurso | URL |
|---------|-----|
| UI ledger | http://localhost:3010/incendios |
| API | http://localhost:8010/docs → `/v1/fire/*` |
| Headline 2024 | `GET /v1/fire/ledger?year=2024` → **Bs 870.000** verificable |
| Inventario fuentes | `docs/sources/fire-inventory.md` |

## Definition of Success (S1–S12)

Ejecutar `./scripts/verify_mvp.sh`:

| ID | Criterio |
|----|----------|
| S1 | Stack health 200 |
| S2 | Migraciones aplicadas |
| S3 | Seed demo sin red |
| S4 | Contract tests offline |
| S5 | AGETIC path (fixture o live opcional) |
| S6 | SICOES parse sample |
| S7 | `GET /v1/contracts` schema OK |
| S8 | ≥1 alerta con explanation |
| S9 | UI smoke Playwright |
| S10 | Docs legales + fichas fuente |
| S11 | LICENSE, CoC, CONTRIBUTING, `.env.example` |
| S12 | Provenance `source_id` + `ingestion_run_id` |
| S13 | Health reporta bloque `proxy` |
| S14 | Serie histórica multi-año + UI `/historico` |

## Licencia

Código: [Apache-2.0](LICENSE). Datos derivados: atribución por fuente; respetar licencias de datos.gob.bo.

## Ética

Ver [`docs/legal/data-policy.md`](docs/legal/data-policy.md). No scrapear datos reservados ni DJBR con CAPTCHA/login.
