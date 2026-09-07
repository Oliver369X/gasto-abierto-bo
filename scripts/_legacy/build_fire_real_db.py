#!/usr/bin/env python3
"""
Build AURA Incendios real-evidence database from downloaded official PDFs.

Honesty rules:
- Only amounts/metrics with page+quote from official docs enter as quality A/B.
- Synthetic SICOES placeholders are tagged is_synthetic=true (not “real spend”).
- Generic emergencia/desastre/sequía pools are no_relacionado or parcial.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "extracted"
FIXTURES = ROOT / "tests" / "fixtures"
OUT.mkdir(parents=True, exist_ok=True)

MINDEF_RPC_2024 = RAW / "mindef" / "rpc_final_2024.pdf"
SHA_RPC_2024 = hashlib.sha256(MINDEF_RPC_2024.read_bytes()).hexdigest()


def extract_fire_snippets(pdf_path: Path, max_pages: int | None = None) -> list[dict]:
    hits: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        pages = pdf.pages[:max_pages] if max_pages else pdf.pages
        for i, page in enumerate(pages, start=1):
            text = page.extract_text() or ""
            if not re.search(
                r"incendio|forestal|VIDECI|aeronave|bombero|Guardian|fuego|quemad",
                text,
                re.I,
            ):
                continue
            hits.append({"page": i, "text": text[:4000], "chars": len(text)})
    return hits


def build_mindef_2024_real() -> dict:
    """Structured facts verified against rpc_final_2024.pdf pages 13–15, 28–29."""
    url = (
        "https://www.mindef.gob.bo/wp-content/uploads/2026/01/"
        "12032025_INFORME_RPCFinal_2024_V15.pdf"
    )
    ops = [
        {
            "record_type": "fire_operational",
            "year": 2024,
            "metric_key": "procesos_aeronaves",
            "metric_label": "Procesos de contratación de alquiler de aeronaves (incendios)",
            "value_numeric": 4,
            "unit": "procesos",
            "entity_name": "Ministerio de Defensa",
            "evidence_page": 28,
            "evidence_quote": (
                "4 Procesos de Contratación de Alquiler Aeronaves Para Lucha Contra Incendios concluidos"
            ),
            "quality_grade": "A",
            "source_document_sha256": SHA_RPC_2024,
        },
        {
            "record_type": "fire_operational",
            "year": 2024,
            "metric_key": "bomberos_forestales",
            "metric_label": "Bomberos forestales movilizados",
            "value_numeric": 9533,
            "unit": "personas",
            "entity_name": "Ministerio de Defensa",
            "evidence_page": 29,
            "evidence_quote": "9.533 bomberos forestales movilizados",
            "quality_grade": "A",
            "source_document_sha256": SHA_RPC_2024,
        },
        {
            "record_type": "fire_operational",
            "year": 2024,
            "metric_key": "unidades_militares",
            "metric_label": "Unidades militares movilizadas",
            "value_numeric": 95,
            "unit": "unidades",
            "entity_name": "Ministerio de Defensa",
            "evidence_page": 29,
            "evidence_quote": "95 Unidades Militares movilizadas",
            "quality_grade": "A",
            "source_document_sha256": SHA_RPC_2024,
        },
        {
            "record_type": "fire_operational",
            "year": 2024,
            "metric_key": "operaciones",
            "metric_label": "Operaciones ejecutadas (CCREA — incendios)",
            "value_numeric": 851,
            "unit": "operaciones",
            "entity_name": "Ministerio de Defensa",
            "evidence_page": 29,
            "evidence_quote": "851 operaciones ejecutadas",
            "quality_grade": "A",
            "source_document_sha256": SHA_RPC_2024,
        },
        {
            "record_type": "fire_operational",
            "year": 2024,
            "metric_key": "estimulacion_nubes",
            "metric_label": "Operaciones de estimulación de nubes",
            "value_numeric": 9,
            "unit": "operaciones",
            "entity_name": "Ministerio de Defensa",
            "evidence_page": 29,
            "evidence_quote": "9 operaciones de estimulación de nubes realizadas",
            "quality_grade": "A",
            "source_document_sha256": SHA_RPC_2024,
        },
        {
            "record_type": "fire_operational",
            "year": 2024,
            "metric_key": "descargas_guardian",
            "metric_label": "Operaciones de descargas del Sistema Guardian",
            "value_numeric": 65,
            "unit": "descargas",
            "entity_name": "Ministerio de Defensa",
            "evidence_page": 29,
            "evidence_quote": "65 operaciones de descargas del Sistema Guardian",
            "quality_grade": "A",
            "source_document_sha256": SHA_RPC_2024,
        },
        {
            "record_type": "fire_operational",
            "year": 2024,
            "metric_key": "descargas_agua",
            "metric_label": "Operaciones de descarga de agua",
            "value_numeric": 3845,
            "unit": "descargas",
            "entity_name": "Ministerio de Defensa",
            "evidence_page": 29,
            "evidence_quote": "3.845 operaciones de descarga de agua ejecutadas",
            "quality_grade": "A",
            "source_document_sha256": SHA_RPC_2024,
        },
        {
            "record_type": "fire_operational",
            "year": 2024,
            "metric_key": "litros_agua",
            "metric_label": "Litros de agua utilizados",
            "value_numeric": 4871620,
            "unit": "litros",
            "entity_name": "Ministerio de Defensa",
            "evidence_page": 29,
            "evidence_quote": "4.871.620 litros de agua utilizados",
            "quality_grade": "A",
            "source_document_sha256": SHA_RPC_2024,
        },
        {
            "record_type": "fire_operational",
            "year": 2024,
            "metric_key": "incendios_mitigados",
            "metric_label": "Incendios forestales mitigados (apagados)",
            "value_numeric": 92,
            "unit": "incendios",
            "entity_name": "Ministerio de Defensa",
            "evidence_page": 29,
            "evidence_quote": "92 incendios forestales mitigados (apagados)",
            "quality_grade": "A",
            "source_document_sha256": SHA_RPC_2024,
        },
        {
            "record_type": "fire_operational",
            "year": 2024,
            "metric_key": "dias_operaciones",
            "metric_label": "Días trabajados CCREA incendios",
            "value_numeric": 156,
            "unit": "días",
            "entity_name": "Ministerio de Defensa",
            "evidence_page": 29,
            "evidence_quote": "156 días trabajados desde 3 de junios a 5 de noviembre 2024",
            "quality_grade": "A",
            "source_document_sha256": SHA_RPC_2024,
        },
        {
            "record_type": "fire_operational",
            "year": 2024,
            "metric_key": "ugr_fortalecidas",
            "metric_label": "Unidades de Gestión de Riesgo fortalecidas",
            "value_numeric": 78,
            "unit": "UGR",
            "entity_name": "Ministerio de Defensa",
            "evidence_page": 27,
            "evidence_quote": "78 Unidades de Gestión de Riesgo (UGR's) fortalecidas",
            "quality_grade": "B",
            "attribution_note": "prevención/preparación multi-riesgo, no solo incendios",
            "source_document_sha256": SHA_RPC_2024,
        },
        {
            "record_type": "fire_operational",
            "year": 2024,
            "metric_key": "municipios_capacitados_riesgo",
            "metric_label": "Municipios de alto/muy alto riesgo capacitados",
            "value_numeric": 47,
            "unit": "municipios",
            "entity_name": "Ministerio de Defensa",
            "evidence_page": 27,
            "evidence_quote": "47 Municipios de alto y muy alto riesgo capacitados técnicamente",
            "quality_grade": "B",
            "attribution_note": "prevención multi-riesgo",
            "source_document_sha256": SHA_RPC_2024,
        },
    ]

    # Monetary lines from same PDF — with honest attribution
    money = [
        {
            "record_type": "fire_expenditure_candidate",
            "code": "FIRE-BO-2024-REAL-DON-CL",
            "year": 2024,
            "title": "Donación logística Bolivia→Chile (incendios forestales)",
            "attribution": "directo",
            "cycle": "respuesta",
            "amount_bob": 870000,
            "quality_grade": "A",
            "paying_entity": "Ministerio de Defensa",
            "beneficiary_note": "Chile (ayuda exterior, no territorio BO)",
            "evidence_page": 28,
            "evidence_quote": (
                "INCENDIOS FORESTALES: Logística y transporte de donaciones ... "
                "con un presupuesto de Bs. 870.000"
            ),
            "source_document_sha256": SHA_RPC_2024,
            "source_url": url,
        },
        {
            "record_type": "fire_expenditure_candidate",
            "code": "FIRE-BO-2024-REAL-HUM-POOL",
            "year": 2024,
            "title": "Atención humanitaria por emergencias (pool multi-evento)",
            "attribution": "no_relacionado",
            "cycle": "respuesta",
            "amount_bob": 18858920,
            "quality_grade": "A",
            "paying_entity": "Ministerio de Defensa",
            "attribution_reason": (
                "Texto oficial no separa incendios; incluye todos los eventos adversos. "
                "NO sumar al ledger incendio como 100%."
            ),
            "evidence_page": 28,
            "evidence_quote": "Bs. 18.858.920 destinado a la atención humanitaria.",
            "source_document_sha256": SHA_RPC_2024,
            "source_url": url,
        },
        {
            "record_type": "fire_expenditure_candidate",
            "code": "FIRE-BO-2024-REAL-SEQ",
            "year": 2024,
            "title": "Plan sequía Agua para la Vida (MINDEF/MMAyA/MDRyT)",
            "attribution": "no_relacionado",
            "cycle": "respuesta",
            "amount_bob": 116087763,
            "quality_grade": "A",
            "paying_entity": "Ministerio de Defensa (+ interinstitucional)",
            "attribution_reason": "Plan de sequía explícito; no es gasto de incendios.",
            "evidence_page": 28,
            "evidence_quote": (
                "Plan Plurinacional de Respuesta Inmediata a la Sequía ... "
                "ejecutado con un presupuesto de Bs. 116.087.763"
            ),
            "source_document_sha256": SHA_RPC_2024,
            "source_url": url,
        },
        {
            "record_type": "fire_expenditure_candidate",
            "code": "FIRE-BO-2024-REAL-CAM",
            "year": 2024,
            "title": "Reconstrucción caminera por eventos adversos",
            "attribution": "no_relacionado",
            "cycle": "recuperacion",
            "amount_bob": 9996850,
            "quality_grade": "A",
            "paying_entity": "Ministerio de Defensa",
            "attribution_reason": "Caminera por eventos adversos; no tipificado como incendio.",
            "evidence_page": 28,
            "evidence_quote": (
                "Reconstrucción Caminera por eventos adversos realizado con un "
                "presupuesto de Bs. 9.996.850"
            ),
            "source_document_sha256": SHA_RPC_2024,
            "source_url": url,
        },
        {
            "record_type": "fire_expenditure_candidate",
            "code": "FIRE-BO-2024-REAL-REHAB",
            "year": 2024,
            "title": "Rehabilitación/reconstrucción a familias (eventos adversos)",
            "attribution": "parcial",
            "cycle": "recuperacion",
            "amount_bob": 16635366,
            "amount_attributed_bob": None,
            "quality_grade": "B",
            "paying_entity": "Ministerio de Defensa",
            "attribution_reason": (
                "Puede incluir familias afectadas por incendios, pero el PDF no desagrega. "
                "amount_attributed=null hasta prueba adicional."
            ),
            "evidence_page": 28,
            "evidence_quote": "Bs. 16.635.366 destinado a las familias afectadas.",
            "source_document_sha256": SHA_RPC_2024,
            "source_url": url,
        },
        {
            "record_type": "fire_expenditure_candidate",
            "code": "FIRE-BO-2024-REAL-DON-TOTAL",
            "year": 2024,
            "title": "Total donaciones Bolivia a países vecinos",
            "attribution": "parcial",
            "cycle": "respuesta",
            "amount_bob": 2793187,
            "quality_grade": "A",
            "paying_entity": "Ministerio de Defensa",
            "attribution_reason": (
                "Incluye Chile incendios (870k) + Palestina + Brasil inundaciones. "
                "Solo 870k es directo incendio."
            ),
            "evidence_page": 29,
            "evidence_quote": (
                "En total el presupuesto de las donaciones de Bolivia a países vecinos "
                "fue de Bs. 2.793.187"
            ),
            "source_document_sha256": SHA_RPC_2024,
            "source_url": url,
        },
        {
            "record_type": "budget_context",
            "year": 2024,
            "entity_name": "Ministerio de Defensa",
            "metric_key": "presupuesto_vigente_total",
            "amount_bob": 3723042901,
            "executed_bob": 3509384238,
            "pct_executed": 94.3,
            "evidence_page": 13,
            "evidence_quote": (
                "presupuesto vigente del Ministerio de Defensa al 31/12/2024 fue de "
                "Bs. 3.723.042.901 ... ejecución alcanzó al 94,3%"
            ),
            "quality_grade": "A",
            "note": "Contexto institucional; NO es presupuesto de incendios.",
            "source_document_sha256": SHA_RPC_2024,
        },
        {
            "record_type": "budget_context",
            "year": 2024,
            "entity_name": "Ministerio de Defensa",
            "metric_key": "grupo_20000_servicios_no_personales",
            "amount_bob": 326062802,
            "executed_bob": 240614033,
            "evidence_page": 14,
            "evidence_quote": (
                "SERVICIOS NO PERSONALES ... 326.062.802 vigente / 240.614.033 ejecutado"
            ),
            "quality_grade": "A",
            "note": (
                "Incluye alquileres/transportes donde podrían estar aeronaves, "
                "pero sin desglose incendio → no atribuir."
            ),
            "source_document_sha256": SHA_RPC_2024,
        },
        {
            "record_type": "budget_context",
            "year": 2024,
            "entity_name": "Fuerza Aérea Boliviana",
            "metric_key": "presupuesto_da_fab",
            "amount_bob": 160200303,
            "executed_bob": 70525226,
            "pct_executed": 44.0,
            "evidence_page": 15,
            "evidence_quote": "Fuerza Aérea Boliviana 160.200.303 / 70.525.226 / 44,0%",
            "quality_grade": "A",
            "note": "Presupuesto FAB completo; no tipificado como incendio.",
            "source_document_sha256": SHA_RPC_2024,
        },
    ]

    # Confirmed aircraft processes WITHOUT fake CUCE amounts
    aircraft_pending = [
        {
            "record_type": "fire_expenditure_candidate",
            "code": f"FIRE-BO-2024-AERO-PROC-{i:02d}",
            "year": 2024,
            "title": f"Proceso {i}/4 alquiler aeronaves lucha contra incendios (monto SICOES pendiente)",
            "attribution": "directo",
            "cycle": "respuesta",
            "amount_bob": None,
            "quality_grade": "B",
            "paying_entity": "Ministerio de Defensa",
            "beneficiary_territory": "Bolivia (nacional / foco SCZ-Beni)",
            "evidence_page": 28,
            "evidence_quote": (
                "4 Procesos de Contratación de Alquiler Aeronaves Para Lucha Contra Incendios concluidos"
            ),
            "pending_sicoes": True,
            "source_document_sha256": SHA_RPC_2024,
            "source_url": url,
            "process_index": i,
        }
        for i in range(1, 5)
    ]

    return {
        "document": {
            "url": url,
            "mime": "application/pdf",
            "sha256": SHA_RPC_2024,
            "local_path": str(MINDEF_RPC_2024.relative_to(ROOT)),
            "pages": 32,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "quality": "A",
        },
        "records": ops,
        "money_and_budget": money,
        "aircraft_processes_pending_amount": aircraft_pending,
    }


def build_hectares_contrast() -> list[dict]:
    """Cross-source burned area estimates (external vs official narrative)."""
    return [
        {
            "metric_key": "hectareas_quemadas_nacional_2024",
            "value": 12600000,
            "unit": "ha",
            "source": "Defensoría del Pueblo / EFE (swissinfo 2025-04-26)",
            "url": "https://www.swissinfo.ch/spa/defensor%C3%ADa-de-bolivia-lamenta-da%C3%B1o-de-12,6-millones-de-hect%C3%A1reas-por-incendios-en-2024/89220929",
            "quality_grade": "C",
            "note": "Cifra citada por Defensoría; no es mapa satelital propio.",
        },
        {
            "metric_key": "hectareas_quemadas_nacional_2024",
            "value": 14000000,
            "unit": "ha",
            "source": "Geomática ambiental / Sumando Voces (eju.tv 2025-01)",
            "url": "https://eju.tv/2025/01/un-equipo-de-geomatica-ambiental-establece-que-en-bolivia-se-quemaron-14-millones-de-hectareas-en-2024/",
            "quality_grade": "C",
            "breakdown": {
                "Santa Cruz": 9149469,
                "Beni": 3888879,
                "La Paz": 500000,
                "Pando": 171616,
            },
        },
        {
            "metric_key": "hectareas_quemadas_nacional_2024",
            "value": 9800000,
            "unit": "ha",
            "source": "Medios (La Nueva, oct 2024 — corte temporal)",
            "url": "https://www.lanueva.com/nota/2024-10-15-8-39-0-bolivia-enfrenta-su-peor-desastre-ambiental-con-9-8-millones-de-hectareas-quemadas",
            "quality_grade": "D",
            "note": "Corte de octubre; subestima total de temporada.",
        },
        {
            "metric_key": "presupuesto_prevencion_anunciado_2025",
            "value": 20000000,
            "unit": "BOB",
            "source": "Anuncio gubernamental 2025 (medios)",
            "url": "https://www.instantaneas.tic.bo/2025/07/06/medio-ambiente/gobierno-destina-bs-20-millones-combatir-incendios-forestales/",
            "quality_grade": "C",
            "note": "Anuncio político Bs 20M 2025 — verificar en ejecución presupuestaria.",
        },
        {
            "metric_key": "fondos_reesignados_incendio_a_inundacion_usd",
            "value": 75000000,
            "unit": "USD",
            "source": "VIDECI vía medios (instantaneas.tic.bo)",
            "url": "https://www.instantaneas.tic.bo/2025/09/11/politica/fondos-incendios-redestinados-inundaciones-bolivia/",
            "quality_grade": "D",
            "note": "Requiere contraste con crédito BID / ejecución MEFP.",
        },
    ]


def scan_pdf_catalog() -> list[dict]:
    catalog = []
    for pdf in sorted(RAW.rglob("*.pdf")):
        size = pdf.stat().st_size
        if size < 1000:
            catalog.append(
                {
                    "path": str(pdf.relative_to(ROOT)),
                    "bytes": size,
                    "status": "invalid_or_404",
                }
            )
            continue
        sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
        # light text probe first 5 + last 2 pages for fire keywords
        fire_pages = 0
        page_count = 0
        try:
            with pdfplumber.open(pdf) as doc:
                page_count = len(doc.pages)
                sample_idx = list(range(min(5, page_count)))
                if page_count > 7:
                    sample_idx += [page_count - 2, page_count - 1]
                for i in sample_idx:
                    t = doc.pages[i].extract_text() or ""
                    if re.search(r"incendio|forestal|fuego|VIDECI|quemad", t, re.I):
                        fire_pages += 1
        except Exception as e:
            catalog.append(
                {
                    "path": str(pdf.relative_to(ROOT)),
                    "bytes": size,
                    "sha256": sha,
                    "status": f"parse_error:{type(e).__name__}",
                }
            )
            continue
        catalog.append(
            {
                "path": str(pdf.relative_to(ROOT)),
                "bytes": size,
                "sha256": sha,
                "pages": page_count,
                "fire_keyword_sample_hits": fire_pages,
                "status": "ok",
            }
        )
    return catalog


def write_updated_fixture(mindef: dict) -> None:
    fixture = {
        "document": mindef["document"],
        "records": mindef["records"],
    }
    path = FIXTURES / "mindef" / "rpc_2024.json"
    path.write_text(json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Updated fixture {path}")

    # Tag synthetic SICOES clearly
    aero_path = FIXTURES / "sicoes" / "fire_2024" / "aeronaves.json"
    aero = json.loads(aero_path.read_text(encoding="utf-8"))
    for r in aero.get("records", []):
        r["is_synthetic"] = True
        r["quality_grade"] = "E"
        r["warning"] = (
            "PLACEHOLDER — montos/CUCEs/proveedores NO verificados en SICOES live. "
            "MINDEF RPC solo confirma 4 procesos sin montos. No usar como gasto real."
        )
    aero["meta"] = {
        "synthetic": True,
        "reason": "Bridge until LIVE_SCRAPE + PROXY_URL unlocks real SICOES CUCEs",
        "confirmed_by_mindef_rpc": {
            "procesos": 4,
            "sha256": SHA_RPC_2024,
            "page": 28,
        },
    }
    aero_path.write_text(json.dumps(aero, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Tagged synthetic {aero_path}")


def main() -> None:
    print("Building MINDEF 2024 real evidence…")
    mindef = build_mindef_2024_real()
    print("Scanning PDF catalog…")
    catalog = scan_pdf_catalog()
    hectares = build_hectares_contrast()

    # SERNAP / ABT light extracts
    extras = {}
    for key, rel in [
        ("sernap_rpc_2024", "sernap/rpc_final_2024.pdf"),
        ("abt_plan_fuego", "abt/plan_accion_gestion_fuego.pdf"),
        ("mindef_rpc_2023", "mindef/rpc_final_2023.pdf"),
        ("mindef_rpc_inicial_2025", "mindef/rpc_inicial_2025.pdf"),
    ]:
        path = RAW / rel
        if path.exists() and path.stat().st_size > 10_000:
            print(f"Sampling {rel}…")
            # Cap pages for huge SERNAP
            max_p = 40 if "sernap" in rel else None
            extras[key] = {
                "path": str(path.relative_to(ROOT)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "fire_snippets": extract_fire_snippets(path, max_pages=max_p)[:25],
            }

    db = {
        "title": "AURA Incendios — base contrastada multi-fuente",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "methodology": {
            "hierarchy": "API → files → XHR → HTML → Playwright → PDF text → OCR",
            "attribution": ["directo", "probable", "parcial", "indirecto", "no_relacionado"],
            "quality": "A=PDF oficial verificado página+cita; B=oficial parcial; C=prensa/institucional secundario; D=corte temporal/placeholder; E=sintético",
            "proxy_note": "SICOES live bloqueado sin PROXY_URL; contratos aeronaves montos = E hasta live",
        },
        "mindef_rpc_2024": mindef,
        "hectares_and_announcements_contrast": hectares,
        "pdf_catalog": catalog,
        "extra_source_samples": {
            k: {
                "path": v["path"],
                "sha256": v["sha256"],
                "snippet_count": len(v["fire_snippets"]),
                "snippets": v["fire_snippets"][:8],
            }
            for k, v in extras.items()
        },
        "ledger_rules_applied": {
            "summable_as_fire_direct_bob": 870000,
            "summable_note": "Solo donación Chile incendios tiene monto + tipificación incendio en PDF.",
            "confirmed_aircraft_processes": 4,
            "aircraft_amounts_bob": None,
            "do_not_sum_as_100pct_fire": [
                18858920,
                116087763,
                9996850,
                16635366,
                2793187,
            ],
        },
    }

    out_path = OUT / "fire_real_db.json"
    out_path.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} ({out_path.stat().st_size} bytes)")

    # Compact contrast table for humans
    contrast = {
        "verificado_oficial_mindef_rpc_2024": {
            "procesos_aeronaves": 4,
            "bomberos": 9533,
            "unidades_militares": 95,
            "operaciones": 851,
            "descargas_agua": 3845,
            "litros_agua": 4871620,
            "incendios_mitigados": 92,
            "dias": 156,
            "ventana": "2024-06-03 → 2024-11-05",
            "donacion_chile_incendios_bob": 870000,
            "sha256": SHA_RPC_2024,
        },
        "hectareas_nacional_rango_fuentes": {
            "min_citado": 9800000,
            "defensoria": 12600000,
            "geomatica": 14000000,
            "disagreement_pct_approx": round((14 - 9.8) / 9.8 * 100, 1),
        },
        "synthetic_pending": {
            "sicoes_aeronaves_amounts": "quality E — no CUCE real aún",
        },
    }
    (OUT / "fire_contrast_summary.json").write_text(
        json.dumps(contrast, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_updated_fixture(mindef)
    print("Done.")


if __name__ == "__main__":
    main()
