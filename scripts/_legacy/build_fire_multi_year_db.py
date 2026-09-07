#!/usr/bin/env python3
"""
Build multi-year AURA Incendios evidence DB from ALL MINDEF RPCs (+ key plans).
Parses each year independently — not just 2024.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "extracted"
OUT.mkdir(parents=True, exist_ok=True)

# Prefer canonical copies (our named files + newly downloaded originals)
MINDEF_DOCS = [
    # (year, kind, path relative to raw)
    (2022, "rpc_inicial", "mindef/RENDICION-DE-CUENTAS-INICIAL-2022.pdf"),
    (2022, "rpc_final", "mindef/RENDICION-DE-CUENTAS-FINAL-2022.pdf"),
    (2022, "rpc_final_alt", "mindef/rpc_final_2022.pdf"),
    (2023, "rpc_final", "mindef/Final_2023.pdf"),
    (2023, "rpc_informe", "mindef/informe23.pdf"),
    (2024, "rpc_inicial", "mindef/Inicial_2024.pdf"),
    (2024, "rpc_final", "mindef/rpc_final_2024.pdf"),
    (2025, "rpc_inicial", "mindef/rpc_inicial_2025.pdf"),
    (2025, "rpc_final", "mindef/rpc_final_2025.pdf"),
    (2026, "rpc_inicial", "mindef/RENDICION-PUBLICA-DE-CUENTAS-INICIAL-GESTION_2026.pdf"),
]

PLAN_DOCS = [
    ("plan_contingencias_2022", "mindef/plan_nacional_contingencias_incendios_2022.pdf"),
    ("plan_prevencion_2026", "planificacion/plan_prevencion_if_2026.pdf"),
    ("abt_plan_fuego", "abt/plan_accion_gestion_fuego.pdf"),
]

# Patterns: (metric_key, regex with one capture group for number, unit, label)
METRIC_PATTERNS = [
    ("procesos_aeronaves", r"(\d+)\s*[Pp]rocesos?\s+de\s+[Cc]ontrataci[oó]n\s+de\s+[Aa]lquiler\s+[Aa]eronaves", "procesos", "Procesos alquiler aeronaves incendios"),
    ("procesos_aeronaves", r"(\d+)\s*[Pp]rocesos?\s+de\s+[Cc]ontrataci[oó]n\s+de\s+[Aa]eronaves", "procesos", "Procesos contratacion aeronaves"),
    ("bomberos_forestales", r"([\d\.]+)\s*[Bb]omberos?\s+forestales", "personas", "Bomberos forestales movilizados"),
    ("unidades_militares", r"([\d\.]+)\s*[Uu]nidades?\s+[Mm]ilitares", "unidades", "Unidades militares movilizadas"),
    ("operaciones", r"([\d\.]+)\s*[Oo]peraciones\s+ejecutadas", "operaciones", "Operaciones ejecutadas"),
    ("descargas_agua", r"([\d\.]+)\s*[Oo]peraciones\s+de\s+descarga\s+de\s+agua", "descargas", "Descargas de agua"),
    ("litros_agua", r"([\d\.]+)\s*[Ll]itros\s+de\s+agua", "litros", "Litros de agua"),
    ("incendios_mitigados", r"([\d\.]+)\s*[Ii]ncendios\s+forestales\s+mitigados", "incendios", "Incendios mitigados"),
    ("incendios_mitigados", r"([\d\.]+)\s*[Ii]ncendios\s+forestales\s+(?:apagados|sofocados)", "incendios", "Incendios sofocados"),
    ("focos_atendidos", r"([\d\.]+)\s*[Ff]ocos\s+(?:de\s+calor\s+)?(?:atendidos|controlados)", "focos", "Focos atendidos"),
    ("hectareas", r"([\d\.]+)\s*[Hh]ect[aá]reas?\s+(?:quemadas|afectadas|intervenidas)", "ha", "Hectareas mencionadas"),
    ("dias_operaciones", r"([\d\.]+)\s*[Dd][ií]as\s+(?:trabajados|de\s+operaciones)", "dias", "Dias de operaciones"),
    ("ugr_fortalecidas", r"([\d\.]+)\s*[Uu]nidades\s+de\s+[Gg]esti[oó]n\s+de\s+[Rr]iesgo", "UGR", "UGR fortalecidas"),
]

MONEY_PATTERNS = [
    ("donacion_chile_incendios", r"[Ii]ncendios?\s+[Ff]orestales[\s\S]{0,200}?Bs\.?\s*([\d\.]+)", "directo", "Donacion/logistica incendios (vecinos)"),
    ("atencion_humanitaria", r"[Aa]tenci[oó]n\s+humanitaria[\s\S]{0,80}?Bs\.?\s*([\d\.]+)", "no_relacionado", "Atencion humanitaria pool"),
    ("presupuesto_sequia", r"[Ss]equ[ií]a[\s\S]{0,120}?Bs\.?\s*([\d\.]+)", "no_relacionado", "Plan sequia"),
    ("reconstruccion_caminera", r"[Rr]econstrucci[oó]n\s+[Cc]aminera[\s\S]{0,80}?Bs\.?\s*([\d\.]+)", "no_relacionado", "Reconstruccion caminera"),
    ("presupuesto_vigente_mindef", r"presupuesto\s+vigente[\s\S]{0,80}?Bs\.?\s*([\d\.]+)", "contexto", "Presupuesto vigente MINDEF"),
    ("presupuesto_ejecutado_mindef", r"ejecuci[oó]n\s+alcanz[\s\S]{0,40}?([\d,\.]+)\s*%|ejecutado[\s\S]{0,40}?Bs\.?\s*([\d\.]+)", "contexto", "Ejecucion presupuestaria"),
]


def parse_num(s: str) -> float:
    s = s.replace(",", "")
    # Bolivian thousands with dots: 9.533 → 9533 if looks like thousands
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        return float(s.replace(".", ""))
    return float(s)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_doc(path: Path, year: int, kind: str, max_pages: int | None = 120) -> dict:
    if not path.exists() or path.stat().st_size < 5000:
        return {"year": year, "kind": kind, "path": str(path), "missing": True}

    fire_text_parts: list[str] = []
    all_text_sample: list[str] = []
    page_hits: list[int] = []
    with pdfplumber.open(path) as pdf:
        pages = pdf.pages[:max_pages] if max_pages else pdf.pages
        n_pages = len(pdf.pages)
        for i, page in enumerate(pages, start=1):
            text = page.extract_text() or ""
            if re.search(r"incendio|VIDECI|aeronave|bombero|forestal|fuego|CCREA", text, re.I):
                fire_text_parts.append(f"\n---PAGE {i}---\n{text}")
                page_hits.append(i)
            if i <= 20 or re.search(r"presupuesto|ejecuci", text, re.I):
                all_text_sample.append(f"\n---PAGE {i}---\n{text[:2500]}")

    fire_blob = "\n".join(fire_text_parts)
    budget_blob = "\n".join(all_text_sample)
    blob = fire_blob + "\n" + budget_blob

    metrics = []
    seen_keys = set()
    for key, pat, unit, label in METRIC_PATTERNS:
        for m in re.finditer(pat, fire_blob, re.I):
            try:
                val = parse_num(m.group(1))
            except Exception:
                continue
            # page hint
            page = None
            before = fire_blob[: m.start()]
            pm = list(re.finditer(r"---PAGE (\d+)---", before))
            if pm:
                page = int(pm[-1].group(1))
            mk = f"{key}:{val}"
            if mk in seen_keys:
                continue
            seen_keys.add(mk)
            metrics.append(
                {
                    "year": year,
                    "metric_key": key,
                    "metric_label": label,
                    "value_numeric": val,
                    "unit": unit,
                    "evidence_page": page,
                    "evidence_quote": m.group(0)[:300],
                    "doc_kind": kind,
                    "quality_grade": "A" if kind.startswith("rpc_final") else "B",
                }
            )

    money = []
    for key, pat, attr, label in MONEY_PATTERNS:
        for m in re.finditer(pat, blob, re.I):
            raw = next((g for g in m.groups() if g), None)
            if not raw:
                continue
            try:
                val = parse_num(raw)
            except Exception:
                continue
            # skip tiny noise
            if val < 100 and attr != "contexto":
                continue
            page = None
            before = blob[: m.start()]
            pm = list(re.finditer(r"---PAGE (\d+)---", before))
            if pm:
                page = int(pm[-1].group(1))
            money.append(
                {
                    "year": year,
                    "metric_key": key,
                    "label": label,
                    "amount_bob": val,
                    "attribution": attr,
                    "evidence_page": page,
                    "evidence_quote": m.group(0)[:400].replace("\n", " "),
                    "doc_kind": kind,
                    "quality_grade": "A" if kind.startswith("rpc_final") else "B",
                }
            )

    return {
        "year": year,
        "kind": kind,
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "pages_total": n_pages,
        "fire_pages": page_hits,
        "metrics": metrics,
        "money": money,
        "fire_chars": len(fire_blob),
    }


def extract_plan(path: Path, key: str) -> dict:
    if not path.exists() or path.stat().st_size < 5000:
        return {"key": key, "missing": True, "path": str(path)}
    hits = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages[:40], start=1):
            text = page.extract_text() or ""
            if re.search(r"incendio|presupuesto|Bs\.|hect|quemad|2020|2019|2021", text, re.I):
                hits.append({"page": i, "text": text[:2000]})
    return {
        "key": key,
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "hits": hits[:20],
        "hit_count": len(hits),
    }


def consolidate(docs: list[dict]) -> dict:
    """Prefer rpc_final over inicial for each year/metric."""
    by_year: dict[int, dict] = {}
    for d in docs:
        if d.get("missing"):
            continue
        y = d["year"]
        slot = by_year.setdefault(
            y,
            {"year": y, "documents": [], "metrics": {}, "money": [], "sha_final": None},
        )
        slot["documents"].append(
            {"kind": d["kind"], "path": d["path"], "sha256": d["sha256"], "fire_pages": d["fire_pages"]}
        )
        if d["kind"].startswith("rpc_final"):
            slot["sha_final"] = d["sha256"]
        for m in d["metrics"]:
            k = m["metric_key"]
            # Prefer final over inicial; prefer larger evidence if same
            prev = slot["metrics"].get(k)
            if not prev:
                slot["metrics"][k] = m
            else:
                rank = {"rpc_final": 3, "rpc_final_alt": 3, "rpc_informe": 2, "rpc_inicial": 1}
                if rank.get(d["kind"], 0) >= rank.get(prev.get("doc_kind"), 0):
                    slot["metrics"][k] = m
        for mon in d["money"]:
            slot["money"].append(mon)

    # dedupe money by key+amount
    for y, slot in by_year.items():
        seen = set()
        uniq = []
        for mon in slot["money"]:
            sig = (mon["metric_key"], mon["amount_bob"], mon.get("doc_kind"))
            if sig in seen:
                continue
            seen.add(sig)
            uniq.append(mon)
        slot["money"] = uniq
        slot["metrics"] = list(slot["metrics"].values())
    return by_year


def main() -> None:
    docs = []
    for year, kind, rel in MINDEF_DOCS:
        path = RAW / rel
        # dedupe same file via different names (rpc_final_2022 vs RENDICION...FINAL)
        print(f"Extracting {year} {kind} {rel}…")
        # Large 2025/2026 finals
        cap = 150 if year >= 2025 else 80
        docs.append(extract_doc(path, year, kind, max_pages=cap))
        print(
            f"  metrics={len(docs[-1].get('metrics') or [])} "
            f"money={len(docs[-1].get('money') or [])} "
            f"fire_pages={docs[-1].get('fire_pages')}"
        )

    plans = []
    for key, rel in PLAN_DOCS:
        print(f"Plan {key}…")
        plans.append(extract_plan(RAW / rel, key))

    by_year = consolidate(docs)
    # Build ledger candidates multi-year
    expenditures = []
    operations = []
    for y, slot in sorted(by_year.items()):
        for m in slot["metrics"]:
            operations.append(
                {
                    "record_type": "fire_operational",
                    "year": y,
                    "metric_key": m["metric_key"],
                    "metric_label": m["metric_label"],
                    "value_numeric": m["value_numeric"],
                    "unit": m["unit"],
                    "entity_name": "Ministerio de Defensa",
                    "evidence_page": m.get("evidence_page"),
                    "evidence_quote": m.get("evidence_quote"),
                    "quality_grade": m.get("quality_grade", "B"),
                    "source_document_sha256": slot.get("sha_final"),
                    "source_id": "mindef_rpc_real",
                }
            )
        for mon in slot["money"]:
            if mon["attribution"] == "contexto":
                continue
            code = f"FIRE-BO-{y}-REAL-{mon['metric_key'].upper()[:20]}"
            expenditures.append(
                {
                    "record_type": "fire_expenditure_candidate",
                    "code": code,
                    "year": y,
                    "title": f"{mon['label']} — gestion {y}",
                    "attribution": mon["attribution"],
                    "cycle": "respuesta",
                    "amount_bob": mon["amount_bob"],
                    "quality_grade": mon.get("quality_grade", "B"),
                    "paying_entity": "Ministerio de Defensa",
                    "evidence_page": mon.get("evidence_page"),
                    "evidence_quote": mon.get("evidence_quote"),
                    "source_document_sha256": slot.get("sha_final"),
                    "source_id": "mindef_rpc_real",
                }
            )

    # SERNAP inventory (catalog only — full text later)
    sernap_catalog = []
    for p in sorted((RAW / "sernap").glob("*.pdf")):
        if p.stat().st_size < 5000:
            continue
        sernap_catalog.append(
            {
                "path": str(p.relative_to(ROOT)).replace("\\", "/"),
                "bytes": p.stat().st_size,
                "sha256": sha256(p),
                "name": p.name,
            }
        )

    db = {
        "title": "AURA Incendios — base multi-gestion contrastada",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "years_covered": sorted(by_year.keys()),
        "methodology": {
            "note": "Una gestion no basta. Se parsean RPC MINDEF de cada anio disponible.",
            "quality": "A=rpc_final tipificado; B=rpc_inicial/parcial; E=sintetico SICOES",
        },
        "by_year": {str(k): v for k, v in sorted(by_year.items())},
        "operations": operations,
        "expenditure_candidates": expenditures,
        "plans": plans,
        "sernap_catalog": sernap_catalog,
        "document_extracts": [
            {k: d[k] for k in d if k not in ("")}
            for d in docs
            if not d.get("missing")
        ],
    }
    # slim document extracts (drop huge blobs already processed)
    for d in db["document_extracts"]:
        pass

    dest = OUT / "fire_multi_year_db.json"
    dest.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {dest} ({dest.stat().st_size} bytes)")
    print("Years:", sorted(by_year.keys()))
    for y, slot in sorted(by_year.items()):
        print(f"  {y}: metrics={len(slot['metrics'])} money={len(slot['money'])} docs={len(slot['documents'])}")
    print(f"Ops total={len(operations)} exp candidates={len(expenditures)} sernap_pdfs={len(sernap_catalog)}")

    # Human summary
    summary = {
        "years": sorted(by_year.keys()),
        "per_year": {
            str(y): {
                "metrics": {m["metric_key"]: m["value_numeric"] for m in slot["metrics"]},
                "money_keys": [m["metric_key"] for m in slot["money"]],
            }
            for y, slot in sorted(by_year.items())
        },
        "sernap_pdf_count": len(sernap_catalog),
        "sernap_total_mb": round(sum(x["bytes"] for x in sernap_catalog) / 1e6, 1),
    }
    (OUT / "fire_multi_year_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
