# Inventario de evidencia real — AURA Incendios

Actualizado: 2026-07-11. Scripts: `scripts/fetch_fire_sources.py`, `fetch_fire_pdfs.py`, `extract_fire_evidence.py`, `build_fire_real_db.py`.

## Qué es “real” vs sintético

| Capa | Estado | Evidencia |
|------|--------|-----------|
| Ops VIDECI 2024 (bomberos, litros, 4 aeronaves…) | **A** | PDF MINDEF RPC Final 2024, sha `86a38097…`, pp. 28–29 |
| Donación Chile incendios Bs 870.000 | **A** | Mismo PDF p.28 tipificado “INCENDIOS FORESTALES” |
| Pools humanitaria / sequía / caminera | **A como cifra**, atribución `no_relacionado` o `parcial` | Mismo PDF — **no sumar** al ledger incendio |
| Montos CUCE alquiler aeronaves | **E sintético** | Solo consta “4 procesos”; sin CUCE/monto en RPC |
| Hectáreas quemadas 9.8–14 M ha | **C contraste** | Defensoría 12.6M vs geomática 14M vs cortes de prensa |

## Archivos locales

- Raw: `data/raw/{mindef,abt,sernap}/` (~40 MB PDFs oficiales)
- Base contrastada: `data/extracted/fire_real_db.json`
- Resumen: `data/extracted/fire_contrast_summary.json`

## Regla de suma (ledger verificable 2024)

**Sumable como incendio directo con monto:** Bs **870.000** (donación Chile).

**Confirmado sin monto:** 4 procesos aeronaves + métricas operativas CCREA.

**No sumar como 100% incendio:** humanitaria 18.8M + sequía 116M + caminera 10M + rehab 16.6M + donaciones vecinos 2.8M.

## Pendiente para subir calidad a A en contratos

1. `PROXY_URL` + `LIVE_SCRAPE=1` → SICOES CUCEs reales de alquiler aeronaves.
2. FIRMS `MAP_KEY` Earthdata → detecciones satélite reales (hoy fixture).
3. Gaceta SCZ (SSL verify / proxy) → decretos de emergencia.

## Contraste hectáreas (discrepancia en DB)

- Defensoría / EFE: **12,6 M ha**
- Geomática / Sumando Voces: **14 M ha** (SCZ 9,15M + Beni 3,89M)
- Diferencia relativa ~43% entre mínimos de prensa y geomática
