# Gasto Abierto Bolivia

Plataforma ciudadana **open source** para fiscalizar el gasto público boliviano a partir de fuentes oficiales dispersas ([Presupuesto Abierto](https://abierto.economiayfinanzas.gob.bo/), SICOES, datos.gob.bo, Contraloría, portales de Santa Cruz).

> Capa ciudadana tipo [Dozorro](https://dozorro.org/): consolidar, versionar, alertar y explicar — siempre con enlace a la fuente primaria.

Auditoría completa: [`AUDIT.md`](AUDIT.md)

## Quickstart (local)

```bash
cp .env.example .env
docker compose up -d --build
# esperar ~60s a healthchecks
./scripts/verify_mvp.sh   # o: powershell -File scripts/verify_mvp.ps1
```

Puertos y URLs locales: ver tabla en `docker-compose.yml` (API **8010**, web **3010**, MinIO **9010/9011**).

| Ruta / servicio | Uso |
|-----------------|-----|
| `/docs` (API) | OpenAPI |
| `/presupuesto` | Explorar presupuesto por institución y geografía |
| `/historico` | Serie multi-año |
| `/discrepancias` | Cruce presupuesto ↔ contratos |

### Entorno Python (edición / CLI sin Docker)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### Seed inicial (offline, sin red)

```bash
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile demo
# Serie histórica 2019–2025 (presupuesto + contratos + discrepancias):
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile history
# Product gate G10 (masters, claims, findings, discrepancias):
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile publish
```

**MinIO opcional (poca RAM):** por defecto `MINIO_ENABLED=0` en `.env`. El stack arranca sin MinIO. Descargas de documentos fallan rápido (503) en lugar de colgar. Para raw lake:

```bash
docker compose --profile storage up -d
# y en .env: MINIO_ENABLED=1
```

**Docker con poca RAM (~512MB):** evitá seed history dentro del contenedor API. Usá el host:

```bash
docker compose up -d   # stack completo, sin BOOT_FULL_SEED
LOW_DOCKER_RAM=1 HOST_SEED_HISTORY=1 ./scripts/host_seed_history.sh
# o antes de verify:
LOW_DOCKER_RAM=1 HOST_SEED_HISTORY=1 ./scripts/verify_mvp.sh
```

Variables útiles en `.env`: `SEED_SKIP_STORAGE=1`, `SEED_BATCH_SIZE=25`, `SEED_TIMEOUT_SECONDS=600`.

## Refrescar datos gubernamentales

### Presupuesto Abierto (oficial — preferido)

El CLI descubre URLs directas desde [abierto.economiayfinanzas.gob.bo/descargas](https://abierto.economiayfinanzas.gob.bo/descargas) (sección «Para desarrolladores»: Parquet gasto/ingreso). Si la descarga remota falla, usa fixtures locales empaquetados.

```bash
python -m scripts.cli gasto fetch-presupuesto --list-only   # URLs descubiertas o de .env
python -m scripts.cli gasto fetch-presupuesto                 # descarga o copia fixtures
docker compose run --rm --entrypoint python api -m scripts.cli gasto ingest --source presupuesto_abierto --sync
docker compose run --rm --entrypoint python api -m scripts.cli gasto refresh-stats
```

Opcional: fijar URLs concretas en `.env` (sobreescribe el descubrimiento automático):

```bash
PRESUPUESTO_ABIERTO_DOWNLOAD_URLS=https://abierto.economiayfinanzas.gob.bo/presupuesto/descargas/gasto/ultimo/gasto.parquet
```

Parquet: `pip install -e ".[parquet]"` antes de ingestar archivos `.parquet`.

### SICOES en vivo (requiere proxy)

Por defecto `LIVE_SCRAPE=0` — el worker re-ingesta fixtures offline. Para scrape en vivo:

```bash
# .env
LIVE_SCRAPE=1
PROXY_URL=http://host.docker.internal:7890   # obligatorio si REQUIRE_PROXY_FOR_LIVE=1

docker compose run --rm --entrypoint python worker \
  -m scripts.cli gasto ingest --source sicoes --sync --live
```

Sin `PROXY_URL` el ingest falla de forma explícita (`assert_live_proxy_ok`). Nightly CI usa `PROXY_URL` del secret del repo.

### Contratos (datos.gob.bo / OCP)

```bash
python -m scripts.cli gasto fetch-open-data
docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile real
```

### SICOES live (solo con proxy/VPN)

```bash
# Ver docs/ops.md — LIVE_SCRAPE=1 + PROXY_URL obligatorio
LIVE_SCRAPE=1 docker compose run --rm worker python -m scripts.cli gasto ingest --source sicoes --sync --live
```

## Comandos oficiales (CLI)

Camino único — ver [`docs/runbook-cli.md`](docs/runbook-cli.md):

```bash
python -m scripts.cli --help
python -m scripts.cli gasto seed --profile demo
python -m scripts.cli gasto verify
python -m scripts.cli gasto ingest --source presupuesto_abierto --sync
python -m scripts.cli gasto fetch-presupuesto
python -m scripts.cli fire pipeline --phase f1
python -m scripts.cli fire verify
```

No usar wrappers sueltos en `scripts/_legacy/`.

### Tests (Docker obligatorio para verificación completa)

```powershell
powershell -File .\scripts\setup_venv.ps1
.\.venv\Scripts\Activate.ps1
.\scripts\test_docker.ps1
```

Incluye pytest offline + seed histórico 2019–2025 + check `/v1/history/years`.

API agregados presupuesto: `GET /v1/budgets/aggregate?group_by=department`

## Arquitectura (MVP lean)

- **Python / FastAPI** — API pública de lectura
- **PostgreSQL** — histórico con SCD2 + provenance
- **Redis + ARQ** — cola de jobs de ingesta
- **MinIO** — data lake de raw (HTML/PDF/CSV)
- **Playwright** — scrapers de sitios dinámicos (SICOES)
- **Next.js** — UI ciudadana en español

Kafka / Airflow / Elasticsearch / Kubernetes: documentados para Fase 2 (`docs/roadmap.md`), no desplegados en MVP.

## Fuentes MVP

| Fuente | Adapter | Notas |
|--------|---------|-------|
| Presupuesto Abierto | `presupuesto_abierto` | **CSV/Parquet oficial** desde `/descargas` |
| datos.gob.bo (CKAN) | `agetic` | Bootstrap OCDS / datasets |
| SICOES | `sicoes` | HTML vivo, rate ≤1 rps |
| Contraloría (informes) | `cge` | Solo metadatos públicos |
| GAD / GAM Santa Cruz | `gad_scz`, `gam_scz` | HTML + PDF texto |
| Ministerio de Defensa (RPC) | `mindef` | Vertical AURA Incendios |
| ABT (ejecución) | `abt` | Prevención / bosques |

## AURA Incendios

Vertical de **libro mayor** del gasto en incendios forestales (no una sola cifra oficial consolidada).

```powershell
docker compose up -d --build postgres redis minio api web
python -m scripts.cli fire verify
python -m scripts.cli fire pipeline --phase f1
```

Documentación: [`docs/aura-incendios/DOCKER.md`](docs/aura-incendios/DOCKER.md)

| Recurso | Ruta |
|---------|------|
| UI ledger | `/incendios` |
| API | `/v1/fire/*` en OpenAPI |

## Definition of Success (S1–S14)

Ejecutar `./scripts/verify_mvp.sh` — ver `docs/G10_DOD.md`.

## Licencia

Código: [Apache-2.0](LICENSE). Datos derivados: atribución por fuente; respetar licencias de datos.gob.bo.

## Ética

Ver [`docs/legal/data-policy.md`](docs/legal/data-policy.md). No scrapear datos reservados ni DJBR con CAPTCHA/login. Preferir descargas oficiales sobre scraping frágil.
