# AURA Incendios — gates (Plan 2 + límites de código)

Actualizado 2026-07-14.

## Última verificación (evidencia)

```
pytest fire suite (Docker)     → 134 passed
python -m scripts.cli fire verify → passed=41 failed=0 ALL GATES PASSED
```

| Check | Resultado |
|-------|-----------|
| ledger 2024 directo | **870000** |
| sicoes_offline | 394 |
| clusters FIRMS | 9 |
| samples FIRMS | 0 |
| geojson features | 3 |
| golden classify | ≥80 / coverage ≥90% |
| verify asserts | **41** |
| wrappers fN | ≤25 líneas |
| corpus_v2 SERNAP | 238+ txt pages + OCR |

Comando: `powershell -File .\scripts\verify_fire_plan2.ps1`  
Ops Docker: [`DOCKER.md`](DOCKER.md)

---

## Sprint 0 — Refactor — DONE

✅ [A0.1]
- Qué: paquete `common.fire` + shims
- Archivos: `packages/common/fire/{classify,ledger,rollup,linking,coverage,capability,geo_bbox}.py`
- Comando: `pytest tests/test_fire_classify.py tests/test_fire_ledger_f1.py tests/test_fire_rollup.py -q`
- Assert: 0 failed
- KPI 870k: N/A

✅ [A0.2–A0.4]
- Qué: `worker.fire` phases f1–f13 + verification
- Archivos: `services/worker/fire/**`
- Comando: `python -c "from worker.fire.pipeline import PHASES; print(sorted(PHASES))"`
- Assert: f1…f13 presentes
- KPI 870k: N/A

✅ [A0.5]
- Qué: CLI unificado `python -m scripts.cli fire …`
- Archivos: `scripts/cli/__main__.py`, `scripts/cli/fire.py`
- Comando: `python -m scripts.cli fire pipeline --help`
- Assert: wrappers fN eliminados (usar CLI)
- KPI 870k: N/A

✅ [A0.6]
- Qué: gate sprint 0
- Comando: `pytest …fire…` + `python -m scripts.cli fire verify` (con stack)
- Assert: suite fire 134 passed; verify **41/41**; KPI 870000; offline=394
- KPI 870k: OK

---

## Ola 1 — SERNAP — DONE

✅ [O1.1] Dockerfile tesseract + spa; rebuild documentado  
✅ [O1.2] `extract_sernap_text_pages` → `corpus_v2/sernap/{sha}/page_n.txt`  
✅ [O1.3] OCR scans con cap `SERNAP_OCR_MAX_PAGES`; soft fail `ocr_unavailable`  
✅ [O1.4] `persist_sernap_outputs` sin inventar montos  
✅ [O1.5] `tests/test_fire_sernap_extract.py` + artefactos `f03_sernap_*.json`  
- KPI 870k: OK

## Ola 2 — Clasificador — DONE

✅ [O2.1] vocabulario parcial/indirecto en `common.fire.classify`  
✅ [O2.2] golden ≥80, coverage≥90%  
✅ [O2.3] `f04_reclassify` sin promover a verificable  
✅ [O2.4] gate pytest golden + KPI  
- KPI 870k: OK

## Ola 3 — SICOES live — DONE | BLOCKED soft

✅ [O3.1] `run_enrich` AERO+top CUCE  
✅ [O3.2] dossiers F2 campos enum (sin proveedores inventados)  
✅ [O3.3] sin `PROXY_URL` → `blocked_no_proxy` (exit 0)  
✅ [O3.4] test `test_f5_enrich_soft_blocks_without_proxy`  
- Live enrich: **BLOCKED** hasta `PROXY_URL`  
- KPI 870k: OK

## Ola 4 — Gacetas — DONE

✅ [O4.1] HTML parse `GacetaSczAdapter` + fixture  
✅ [O4.2] `GacetaNacionalAdapter` registrado  
✅ [O4.3] f07 años 2019–2025 `found|none_found` + `attempted_sources`  
✅ [O4.4] `tests/test_fire_gaceta_adapters.py`  
- KPI 870k: OK

## Ola 5 — FIRMS — DONE | BLOCKED soft

✅ [O5.1] live CSV solo con `MAP_KEY` + `FETCH_FIRMS_LIVE=1`  
✅ [O5.2] bbox SCZ/Beni/Pando (`geo_bbox`)  
✅ [O5.3] samples=0; clusters≥1; status blocked|fetched|disabled  
- Live FIRMS: **BLOCKED** sin `MAP_KEY`  
- KPI 870k: OK

## Ola 6 — Capacidad — DONE

✅ [O6.1] `classify_asset` + 12 tests  
✅ [O6.2] upsert por expenditure_id  
✅ [O6.3] `/capabilities/summary` + UI “Capacidad vs reacción”  
✅ [O6.4] gate unitario  
- KPI 870k: OK

## Ola 7 — GeoJSON + mapa — DONE

✅ [O7.1] `GET /v1/fire/coverage.geojson` 3 features + level + amount  
✅ [O7.2] `/incendios/mapa` SVG (sin MapLibre; DoD acepta svg)  
✅ [O7.3] verify incluye geojson features=3 + web mapa 200  
- KPI 870k: OK

---

## F1–F14 (Plan 2 baseline) — DONE

Ver historial anterior: ledger 870k, aeronaves, corpus, backfill, cycles, declarations, FIRMS clusters, events, capability, territorial, links, alerts, producto.

### Pendiente explícito (no código / secretos)
- Proxy real para enrich SICOES
- `MAP_KEY` + `FETCH_FIRMS_LIVE=1` para focos live
- Validación humana OCR SERNAP sobre PDFs grandes
- Inventario físico F10 más allá de títulos de expediente
