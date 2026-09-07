# Evidencia multi-gestión — AURA Incendios

Actualizado: 2026-07-12.

## Alcance (no es solo 2024)

| Capa | Años | Fuente |
|------|------|--------|
| Hectáreas quemadas nacionales | **2000–2025** (26 gestiones) | DGF-SIMB vía Plan Prevención IF 2026 (MDPyEP), Tabla 1 |
| Ops militares / VIDECI | **2022, 2023, 2024, 2025** (+ plan 2026) | MINDEF RPC finales/iniciales |
| Montos tipificados (pools + 1 directo) | **2023–2024** | MINDEF RPC |
| Contraste ABT vs DGF | **2019–2020** | Plan Acción Gestión del Fuego ABT |
| Corpus PDF | **38 PDFs / ~374 MB** | MINDEF + SERNAP 2020–2025 + ABT + Planificación |

## Pico histórico
- **2024: 12.658.157 ha** (DGF-SIMB) — peor gestión de la serie
- 2010: 8.389.907 ha · 2023: 6.382.464 ha · 2022: 4.467.158 ha

## Ops por gestión (MINDEF)
- **2022**: tabla completa lucha incendios (147 mitigaciones, 424 ops, 999.600 L, 5.948 efectivos, desglose por depto)
- **2023**: humanitaria/sequía/caminera tipificados; **sin** tabla CCREA incendio detallada
- **2024**: 4 aeronaves + 9.533 bomberos + 851 ops + Bs 870k donación Chile
- **2025**: UGR/ETA cualitativo; ha DGF 2.090.103

## Scripts
```bash
python scripts/build_fire_all_years_db.py
python scripts/seed_fire_all_years.py   # DATABASE_URL → Postgres
```

Artefactos: `data/extracted/fire_all_years_db.json`, `fire_all_years_summary.json`
