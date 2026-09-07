#!/usr/bin/env python3
"""
Curated multi-year AURA Incendios DB — ALL gestiones with official evidence.
Hand-verified quotes from downloaded PDFs + DGF-SIMB series 2000-2025.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "extracted"
FIXTURES = ROOT / "tests" / "fixtures"


def sha(rel: str) -> str:
    p = RAW / rel
    if not p.exists():
        return ""
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


# Official burned area series — Plan Prevención IF 2026 (DGF-SIMB 2025), Tabla 1 p.7
HECTARES_DGF_SIMB = {
    2000: 24283,
    2001: 1868836,
    2002: 4693297,
    2003: 2616654,
    2004: 5817673,
    2005: 5601132,
    2006: 4162889,
    2007: 3818018,
    2008: 2816848,
    2009: 1921975,
    2010: 8389907,
    2011: 2802567,
    2012: 2571535,
    2013: 1585599,
    2014: 2973466,
    2015: 3799692,
    2016: 5013132,
    2017: 3604823,
    2018: 1826015,
    2019: 5297122,
    2020: 4990136,
    2021: 4199929,
    2022: 4467158,
    2023: 6382464,
    2024: 12658157,
    2025: 2090103,
}

SHA_PPIF = sha("planificacion/plan_prevencion_if_2026.pdf")
SHA_ABT = sha("abt/plan_accion_gestion_fuego.pdf")
SHA_2022 = sha("mindef/RENDICION-DE-CUENTAS-FINAL-2022.pdf")
SHA_2023 = sha("mindef/Final_2023.pdf")
SHA_2024 = sha("mindef/rpc_final_2024.pdf")
SHA_2025 = sha("mindef/rpc_final_2025.pdf")
SHA_2026 = sha("mindef/RENDICION-PUBLICA-DE-CUENTAS-INICIAL-GESTION_2026.pdf")

# MINDEF operational metrics by year (verified from PDF text)
OPS = {
    2022: {
        "source": "mindef/RENDICION-DE-CUENTAS-FINAL-2022.pdf",
        "sha256": SHA_2022,
        "pages": [49, 50],
        "metrics": [
            ("operaciones_mitigacion", 147, "operaciones", 49, "OPERACIONES DE MITIGACIÓN (INTERVENCIÓN A INCENDIOS FORESTALES) 147"),
            ("reconocimiento_aereo", 98, "operaciones", 49, "RECONOCIMIENTO Y EXPLORACIÓN AÉREA 98"),
            ("reconocimiento_terrestre", 54, "operaciones", 49, "RECONOCIMIENTO Y EXPLORACIÓN TERRESTRE 54"),
            ("bambi_bucket_ops", 125, "operaciones", 49, "OPERACIONES DE APOYO AÉREO CON BUMBI BUCKET 125"),
            ("total_operaciones", 424, "operaciones", 49, "TOTAL OPERACIONES 424"),
            ("efectivos_militares_total_con_repetidos", 10716, "personas", 49, "EFECTIVOS MILITARES EMPLEADOS (Total con repetidos) 10.716"),
            ("efectivos_militares_real", 5948, "personas", 49, "TOTAL EFECTIVOS (Real) 5.948"),
            ("descargas_agua", 1428, "descargas", 50, "Total Descargas de Agua 1.428"),
            ("litros_agua", 999600, "litros", 50, "Cantidad de Agua en litros 999.600"),
            ("unidades_militares", 66, "unidades", 50, "TOTAL 66 unidades militares"),
            ("ha_incendios_forestales", 808408, "ha", 50, "INCENDIOS FORESTALES 808.408,00"),
            ("ha_quemas_fiscales", 1191418.81, "ha", 50, "QUEMAS EN PAJONALES... 1.191.418,81"),
            ("ha_quemas_agropecuarios", 2466713.54, "ha", 50, "QUEMAS EN PREDIOS AGROPECUARIOS 2.466.713,54"),
            # Note: PDF OCR/ typo TOTAL 4.0466.540,35 ≈ 4.466.540
            ("ha_superficie_total_mindef", 4466540.35, "ha", 50, "TOTAL 4.0466.540,35 (typo tipográfico en PDF; ~4.466.540)"),
            ("ops_scz_mitigacion", 82, "operaciones", 49, "Santa Cruz 82 operaciones mitigación"),
            ("ops_tarija_mitigacion", 24, "operaciones", 49, "Tarija 24"),
            ("ops_beni_mitigacion", 4, "operaciones", 49, "Beni 4"),
            ("ccrea_creacion", 1, "evento", 46, "CCREA creado 12 mayo 2022, funciones desde 3 junio 2022"),
        ],
        "money": [],
    },
    2023: {
        "source": "mindef/Final_2023.pdf",
        "sha256": SHA_2023,
        "pages": [13, 27, 28],
        "metrics": [
            ("ugr_fortalecidas", 20, "UGR", 28, "20 unidades de gestión de riesgos (UGR's) fortalecidas"),
            ("ugr_municipios_capacitados", 10, "municipios", 28, "10 (UGR's) municipios de alto y muy alto riesgo capacitados"),
            ("municipios_ayuda_humanitaria", 191, "municipios", 27, "191 municipios atendidos"),
            ("familias_damnificadas", 73977, "familias", 27, "73.977 familias damnificadas"),
            ("ops_inundaciones_ccrea", 50, "operaciones", 28, "50 operaciones terrestres, aéreas y fluviales ejecutadas contra inundaciones"),
        ],
        "money": [
            ("atencion_humanitaria", 19862070, "no_relacionado", 27, "Bs. 19.862.070 destinado a la atención humanitaria."),
            ("plan_sequia", 122000000, "no_relacionado", 27, "Plan sequía ejecutado con un presupuesto de Bs. 122.000.000"),
            ("reconstruccion_caminera", 30026885, "no_relacionado", 28, "Reconstrucción Caminera ... Bs. 30.026.885"),
            ("rehab_familias", 7266091, "parcial", 28, "Bs. 7.266.091 destinado a las familias afectadas."),
            ("presupuesto_vigente_mindef", 3638827481, "contexto", 13, "TOTAL vigente 3.638.827.481"),
            ("presupuesto_ejecutado_mindef", 3471849793, "contexto", 13, "TOTAL ejecutado 3.471.849.793 (95,4%)"),
        ],
        "note": "RPC 2023 menciona incendios en presentación pero no publica tabla de ops incendio como 2022/2024.",
    },
    2024: {
        "source": "mindef/rpc_final_2024.pdf",
        "sha256": SHA_2024,
        "pages": [13, 28, 29],
        "metrics": [
            ("procesos_aeronaves", 4, "procesos", 28, "4 Procesos de Contratación de Alquiler Aeronaves Para Lucha Contra Incendios concluidos"),
            ("bomberos_forestales", 9533, "personas", 29, "9.533 bomberos forestales movilizados"),
            ("unidades_militares", 95, "unidades", 29, "95 Unidades Militares movilizadas"),
            ("operaciones", 851, "operaciones", 29, "851 operaciones ejecutadas"),
            ("estimulacion_nubes", 9, "operaciones", 29, "9 operaciones de estimulación de nubes realizadas"),
            ("descargas_guardian", 65, "descargas", 29, "65 operaciones de descargas del Sistema Guardian"),
            ("descargas_agua", 3845, "descargas", 29, "3.845 operaciones de descarga de agua ejecutadas"),
            ("litros_agua", 4871620, "litros", 29, "4.871.620 litros de agua utilizados"),
            ("incendios_mitigados", 92, "incendios", 29, "92 incendios forestales mitigados (apagados)"),
            ("dias_operaciones", 156, "dias", 29, "156 días trabajados desde 3 de junios a 5 de noviembre 2024"),
            ("ugr_fortalecidas", 78, "UGR", 27, "78 Unidades de Gestión de Riesgo (UGR's) fortalecidas"),
        ],
        "money": [
            ("donacion_chile_incendios", 870000, "directo", 28, "INCENDIOS FORESTALES ... presupuesto de Bs. 870.000"),
            ("atencion_humanitaria", 18858920, "no_relacionado", 28, "Bs. 18.858.920 destinado a la atención humanitaria."),
            ("plan_sequia", 116087763, "no_relacionado", 28, "Plan sequía ... Bs. 116.087.763"),
            ("reconstruccion_caminera", 9996850, "no_relacionado", 28, "Reconstrucción Caminera ... Bs. 9.996.850"),
            ("rehab_familias", 16635366, "parcial", 28, "Bs. 16.635.366 destinado a las familias afectadas."),
            ("donaciones_vecinos_total", 2793187, "parcial", 29, "donaciones ... Bs. 2.793.187"),
            ("presupuesto_vigente_mindef", 3723042901, "contexto", 13, "presupuesto vigente ... Bs. 3.723.042.901"),
            ("presupuesto_ejecutado_mindef", 3509384238, "contexto", 13, "ejecutado 3.509.384.238 (94,3%)"),
        ],
    },
    2025: {
        "source": "mindef/rpc_final_2025.pdf",
        "sha256": SHA_2025,
        "pages": [30, 39],
        "metrics": [
            ("ugr_capacitadas", 25, "UGR", 30, "UGR capacitadas 25 UGR Cumplido"),
            ("lineamientos_eta", 12, "lineamientos", 30, "Lineamientos ETA 12 emitidos"),
            ("carros_bomberos_entregados", 1, "mencion", 39, "Se entregaron carros bomberos ... (sin cantidad tipificada en texto)"),
            ("umee_creacion", 1, "evento", 39, "creación de la Unidad Militar de Emergencia y Ecología (UMEE)"),
        ],
        "money": [],
        "note": "RPC Final 2025 reporta cumplimiento VIDECI cualitativo; sin tabla CCREA incendio como 2022/2024. Ha quemadas: serie DGF-SIMB 2.090.103 ha.",
    },
    2026: {
        "source": "mindef/RENDICION-PUBLICA-DE-CUENTAS-INICIAL-GESTION_2026.pdf",
        "sha256": SHA_2026,
        "pages": [39, 48, 50],
        "metrics": [],
        "money": [],
        "note": "RPC Inicial 2026 — planificación; Plan Prevención IF 2026 del Ministerio de Planificación.",
    },
}

# ABT contrast for 2019-2020 (Plan Acción Gestión del Fuego)
ABT_HECTARES = {
    2019: {"nacional": 5337135, "note": "ABT plan: 5.337.135 (ligera diferencia vs DGF-SIMB 5.297.122)"},
    2020: {"nacional": 5021820, "note": "ABT plan: 5.021.820 vs DGF-SIMB 4.990.136"},
}


def build() -> dict:
    operations = []
    expenditures = []
    seasons = []
    discrepancies = []

    for year, ha in sorted(HECTARES_DGF_SIMB.items()):
        operations.append(
            {
                "record_type": "fire_operational",
                "year": year,
                "metric_key": "hectareas_quemadas_dgf_simb",
                "metric_label": "Superficie quemas e incendios (DGF-SIMB)",
                "value_numeric": ha,
                "unit": "ha",
                "entity_name": "DGF - SIMB (vía Plan Prevención IF 2026)",
                "evidence_page": 7,
                "evidence_quote": f"Tabla 1 Plan Prevención IF 2026: {year} = {ha:,} ha",
                "quality_grade": "A",
                "source_document_sha256": SHA_PPIF,
                "source_id": "dgf_simb_ppif2026",
            }
        )

    for year, block in OPS.items():
        grade = "B" if year in (2025, 2026) else "A"
        if year == 2023:
            grade = "B"  # ops incendio incompletas en RPC
        seasons.append(
            {
                "year": year,
                "quality_grade": grade,
                "notes": block.get("note")
                or f"MINDEF RPC + DGF-SIMB ha={HECTARES_DGF_SIMB.get(year)}",
                "source_sha256": block["sha256"],
                "source_path": block["source"],
            }
        )
        for key, val, unit, page, quote in block["metrics"]:
            operations.append(
                {
                    "record_type": "fire_operational",
                    "year": year,
                    "metric_key": key,
                    "metric_label": key.replace("_", " ").title(),
                    "value_numeric": val,
                    "unit": unit,
                    "entity_name": "Ministerio de Defensa",
                    "evidence_page": page,
                    "evidence_quote": quote,
                    "quality_grade": "A" if year in (2022, 2024) else "B",
                    "source_document_sha256": block["sha256"],
                    "source_id": "mindef_rpc_real",
                }
            )
        for key, amt, attr, page, quote in block["money"]:
            if attr == "contexto":
                operations.append(
                    {
                        "record_type": "fire_operational",
                        "year": year,
                        "metric_key": key,
                        "metric_label": key.replace("_", " ").title(),
                        "value_numeric": amt,
                        "unit": "BOB",
                        "entity_name": "Ministerio de Defensa",
                        "evidence_page": page,
                        "evidence_quote": quote,
                        "quality_grade": "A",
                        "source_document_sha256": block["sha256"],
                        "source_id": "mindef_rpc_real",
                        "attribution_note": "contexto institucional, no gasto incendio",
                    }
                )
                continue
            code = f"FIRE-BO-{year}-REAL-{key.upper()[:18]}"
            attributed = amt if attr == "directo" else None
            expenditures.append(
                {
                    "code": code,
                    "year": year,
                    "title": f"{key.replace('_', ' ').title()} — gestión {year}",
                    "attribution": attr,
                    "cycle": "respuesta" if attr != "contexto" else "preparacion",
                    "amount_bob": amt,
                    "amount_attributed_bob": attributed,
                    "quality_grade": "A",
                    "paying_entity": "Ministerio de Defensa",
                    "evidence_page": page,
                    "evidence_quote": quote,
                    "source_document_sha256": block["sha256"],
                    "source_url": f"file://{block['source']}",
                    "source_id": "mindef_rpc_real",
                }
            )

    # Contraste hectáreas ABT vs DGF-SIMB
    for y, abt in ABT_HECTARES.items():
        dgf = HECTARES_DGF_SIMB[y]
        discrepancies.append(
            {
                "concept": f"fire:hectareas_nacional_{y}_abt_vs_dgf",
                "amount_a": abt["nacional"],
                "amount_b": dgf,
                "source_a": "abt_plan_accion_gestion_fuego",
                "source_b": "dgf_simb_ppif2026",
                "ref_a": abt["note"],
                "ref_b": f"DGF-SIMB {dgf:,} ha",
            }
        )
        # also 2022 MINDEF total vs DGF
    discrepancies.append(
        {
            "concept": "fire:hectareas_2022_mindef_vs_dgf",
            "amount_a": 4466540.35,
            "amount_b": 4467158,
            "source_a": "mindef_rpc_final_2022_p50",
            "source_b": "dgf_simb_ppif2026",
            "ref_a": "MINDEF total superficie quema (~4.466.540 con typo PDF)",
            "ref_b": "DGF-SIMB 4.467.158 ha",
        }
    )
    discrepancies.append(
        {
            "concept": "fire:hectareas_2024_defensoria_vs_dgf",
            "amount_a": 12600000,
            "amount_b": 12658157,
            "source_a": "defensoria_pueblo_medios",
            "source_b": "dgf_simb_ppif2026",
            "ref_a": "12,6 M ha citados por Defensoría",
            "ref_b": "DGF-SIMB 12.658.157 ha",
        }
    )

    # Catalog of raw documents
    catalog = []
    for folder in ("mindef", "sernap", "abt", "planificacion"):
        d = RAW / folder
        if not d.exists():
            continue
        for p in sorted(d.glob("*.pdf")):
            if p.stat().st_size < 5000:
                continue
            catalog.append(
                {
                    "source": folder,
                    "path": str(p.relative_to(ROOT)).replace("\\", "/"),
                    "bytes": p.stat().st_size,
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                    "name": p.name,
                }
            )

    return {
        "title": "AURA Incendios — base multi-gestión (2000–2026)",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "years_hectares": list(range(2000, 2026)),
        "years_mindef_ops": sorted(OPS.keys()),
        "hectares_dgf_simb": HECTARES_DGF_SIMB,
        "seasons": seasons,
        "operations": operations,
        "expenditure_candidates": expenditures,
        "discrepancies": discrepancies,
        "abt_contrast": ABT_HECTARES,
        "document_catalog": catalog,
        "honesty": {
            "gasto_directo_tipificado_incendio_con_monto": {
                2024: 870000,
                "note": "Único monto Bs tipificado 'incendios forestales' en RPC MINDEF hallado hasta ahora",
            },
            "ops_ricas": [2022, 2024],
            "ops_parciales": [2023, 2025],
            "sicoes_aeronaves": "aún sintético E — necesita PROXY",
            "serie_ha": "DGF-SIMB vía Plan Prevención IF 2026 (oficial planificación)",
        },
    }


def main() -> None:
    db = build()
    dest = OUT / "fire_all_years_db.json"
    dest.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    # compact summary
    summary = {
        "hectares_peak": max(HECTARES_DGF_SIMB.items(), key=lambda x: x[1]),
        "hectares_2024": HECTARES_DGF_SIMB[2024],
        "hectares_2022": HECTARES_DGF_SIMB[2022],
        "ops_count": len(db["operations"]),
        "exp_count": len(db["expenditure_candidates"]),
        "disc_count": len(db["discrepancies"]),
        "pdf_count": len(db["document_catalog"]),
        "pdf_mb": round(sum(x["bytes"] for x in db["document_catalog"]) / 1e6, 1),
        "years_mindef": db["years_mindef_ops"],
        "direct_spend_by_year": {
            str(e["year"]): e["amount_bob"]
            for e in db["expenditure_candidates"]
            if e["attribution"] == "directo"
        },
    }
    (OUT / "fire_all_years_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Wrote {dest} ({dest.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
