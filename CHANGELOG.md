# Changelog

## [0.7.0] — 2026-07-11

### Added
- Histórico SICOES **todas las gestiones 2007–2026** (~1.5M convocatorias)
  - `download_sicoes_all_years.py` (sociedatos mensual + lab-tecnosocial)
  - `build_sicoes_all_years.py` → corpus por año
  - `seed_all_years.py` (ingest masivo skip alerts/storage)
- Persistencia con cache de entidades/proveedores para cargas grandes

## [0.6.1] — 2026-07-11

### Added
- Pipeline de datos **reales**: `download_real_sources.py` → `build_real_corpus.py` → `seed_real.py`
- Espejo OCP Data Registry (Bolivia AGETIC) + CSV SICOES OCDS de datos.gob.bo
- 8k+ filas de proyectos públicos CKAN como presupuesto contrastable
- Corpus unificado en `tests/fixtures/real/corpus/`

## [0.6.0] — 2026-07-11

### Added
- Corpus profundo multi-año / multi-fuente (`scripts/generate_deep_corpus.py` + `seed_deep.py`)
- Discover profundo: SICOES paginación + años; AGETIC multi-package/`package_search`; PA/CGE multi-URL + dirs
- Cruce de fuentes: `normalize_cuce`, `reconcile` CUCE + presupuesto vs contratos
- API `GET /v1/cross-source/summary`
- Defaults live: `SICOES_MAX_PAGES=25` (no solo 1ª página)

## [0.5.0] — 2026-07-11

### Added
- API: `/v1/search`, `/v1/history/compare`, `/v1/entities/{id}/activity`, detalle discrepancias + `delta_pct`
- UI: detalle alerta, timeline entidad, histórico YoY, explorar unificado, menú móvil
- Seed cross-source SICOES vs AGETIC (`scripts/seed_cross_source.py`) para discrepancias reales

## [0.4.0] — 2026-07-11

### Added
- Scrapers resilientes: HTTP retry/backoff, soft-fail por ítem, `finish_run` ok/partial/error
- Categorización de gasto (`obras|salud|educacion|servicios|bienes|consultoria|otros`)
- API `GET /v1/categories`, filtro `?category=`, backfill `scripts/backfill_categories.py`
- Descarga raw `GET /v1/documents/{id}/download` (presigned MinIO o stream)
- UI blanco/negro limpia; filtros categoría; provenance + raw en contrato/fuentes

## [0.3.0] — 2026-07-11

### Added
- Proxy/VPN obligatorio para scrapes live (`PROXY_URL`, `REQUIRE_PROXY_FOR_LIVE`)
- Fixtures + seed histórico 2019–2025 (`scripts/seed_history.py`)
- API `/v1/history/years`, filtros `year` / `include_history`
- UI `/historico` + filtro año en explorar
- Suite Docker: `scripts/test_docker.ps1` + `docker-compose.test.yml`
- Tests: proxy required, history fixtures

## [0.2.0] — 2026-07-11

### Added
- MinIO raw lake cableado (`packages/common/storage.py` + pipeline)
- CLI `scripts/ingest.py` (--sync / --enqueue / --live)
- API v0.2: `/v1/stats`, `/v1/documents`, `/v1/ingestion-runs`, detalle contrato, filtros
- Alertas v2: nombres legibles + fraccionamiento + baja ejecución
- UI: dashboard, búsqueda, auditorías, discrepancias, fuentes, detalle contrato
- SCD2 real en presupuestos; cruce inter-fuentes por CUCE
- Parser SICOES con monto/proveedor; PDF via pdfplumber
- docs/ops.md + nightly workflow_dispatch live

## [0.1.0-mvp] — 2026-07-11

### Added
- Monorepo OSS: API FastAPI, worker ARQ, Next.js UI, PostgreSQL SCD2 schema
- SourceAdapters: agetic, sicoes, presupuesto_abierto, cge, gad_scz, gam_scz
- Fixtures + contract tests offline
- Explainable alert rules
- Docker Compose stack + verify_mvp scripts
- Docs: architecture, ADRs, legal data-policy, source sheets
