#!/usr/bin/env python3
"""Build a unified REAL+contrast corpus from downloaded open data.

Reads tests/fixtures/real/** and writes:
  tests/fixtures/real/corpus/agetic_contracts.csv
  tests/fixtures/real/corpus/sicoes_contracts.csv   (same CUCEs, amount drift from OCP items vs referential)
  tests/fixtures/real/corpus/projects_as_budget.json
  tests/fixtures/real/corpus/ocp_contracts.csv
"""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REAL = ROOT / "tests" / "fixtures" / "real"
CORPUS = REAL / "corpus"
CORPUS.mkdir(parents=True, exist_ok=True)


def _read_csv(path: Path) -> list[dict]:
    raw = path.read_bytes()
    # encoding guess
    for enc in ("utf-8-sig", "latin-1", "cp1252"):
        try:
            text = raw.decode(enc)
            break
        except Exception:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")
    sample = text[:4096]
    delim = ";" if sample.count(";") > sample.count(",") else ","
    return list(csv.DictReader(text.splitlines(), delimiter=delim))


def normalize_sicoes_ocp(path: Path) -> list[dict]:
    rows = _read_csv(path)
    out = []
    for row in rows:
        # exact field preference (avoid Código_entidad matching "entidad")
        cuce = (
            row.get("CUCE_sicoes")
            or row.get("cuce")
            or row.get("ocid")
            or ""
        ).strip()
        entity = (
            row.get("Nombre_entidad")
            or row.get("nombre_entidad")
            or row.get("organismo")
            or ""
        ).strip()
        # parties often store code in Nombre wrongly — expand known code
        if entity.upper().startswith("BO-COD-") or re.fullmatch(r"BO-COD-\d+-\d+", entity):
            entity = "AGETIC"
        if not entity:
            entity = "Entidad SICOES/AGETIC"
        desc = (
            row.get("Objeto_contratacion_titulo_licitacion")
            or row.get("Items_Descripcion_bienes_servicios")
            or ""
        ).strip()
        amount = (
            row.get("Precio_referencial_total_Monto")
            or row.get("Monto")
            or ""
        ).strip()
        modality = (
            row.get("Modalidad_de_Contratación")
            or row.get("Modalidad_de_Contratacion")
            or row.get("Metodo de seleccion y adjudicación")
            or row.get("Metodo de seleccion y adjudicacion")
            or ""
        ).strip()
        date = (
            row.get("Fecha_de_publicacion_sicoes")
            or row.get("fecha_inicio_proceso_de_contratacion")
            or ""
        ).strip()
        if not cuce:
            continue
        out.append(
            {
                "cuce": cuce,
                "entity": entity,
                "supplier": "",
                "description": desc,
                "amount": amount,
                "modality": modality,
                "date": date,
                "status": "published",
                "department": "",
                "source_note": "datos.gob.bo sicoes_ocp_2019",
            }
        )
    return out


def build_ocp_contracts() -> list[dict]:
    full = REAL / "ocp_agetic" / "download_name_full.csv" / "full"
    if not full.exists():
        return []
    main = {r["_link"]: r for r in _read_csv(full / "main.csv") if r.get("_link") is not None}
    parties = defaultdict(list)
    for r in _read_csv(full / "parties.csv"):
        parties[r.get("_link_main")].append(r)
    suppliers = defaultdict(list)
    for r in _read_csv(full / "awards_suppliers.csv"):
        suppliers[r.get("_link_main")].append(r)
    items = defaultdict(list)
    for r in _read_csv(full / "awards_items.csv"):
        items[r.get("_link_main")].append(r)

    out = []
    for link, m in main.items():
        ocid = (m.get("ocid") or "").strip()
        # CUCE often embedded in ocid: ocds-r7dadk-19-0374-00-1005728-0-E
        cuce = ocid
        if "ocds-r7dadk-" in ocid:
            cuce = ocid.replace("ocds-r7dadk-", "")
        buyer = (m.get("buyer_name") or "").strip()
        if not buyer:
            for p in parties.get(link, []):
                name = (p.get("name") or "").strip()
                if name and not name.upper().startswith("BO-COD"):
                    buyer = name
                    break
            if not buyer and parties.get(link):
                buyer = parties[link][0].get("name") or "AGETIC"
        # sum award item amounts
        total = 0.0
        for it in items.get(link, []):
            for key in ("realValue_amount", "unit_value_amount"):
                v = (it.get(key) or "").strip()
                if not v:
                    continue
                try:
                    total += float(v.replace(",", ""))
                    break
                except ValueError:
                    pass
        sup = ""
        if suppliers.get(link):
            sup = suppliers[link][0].get("name") or ""
        out.append(
            {
                "cuce": cuce or ocid,
                "entity": buyer or "AGETIC",
                "supplier": sup,
                "description": (m.get("tender_title") or "").strip(),
                "amount": f"{total:.2f}" if total else "",
                "modality": (m.get("tender_procurementMethodDetails") or "").strip(),
                "date": (m.get("date") or m.get("tender_tenderPeriod_startDate") or "")[:10],
                "status": (m.get("tag") or "compiled"),
                "department": "",
                "source_note": "OCP registry Bolivia AGETIC",
            }
        )
    return out


def normalize_projects_as_budget() -> list[dict]:
    """Map rural/investment project CSVs -> budget rows (entity/year/amounts)."""
    series: list[dict] = []
    for path in REAL.glob("ckan_*/**/*.csv"):
        if "normalized_" in path.name:
            continue
        if "contrataciones" in str(path).lower() or "sicoes" in path.name.lower():
            continue
        try:
            rows = _read_csv(path)
        except Exception:
            continue
        if not rows:
            continue
        keys = {k.lower(): k for k in rows[0].keys() if k}

        def find(*cands: str) -> str | None:
            for c in cands:
                for lk, orig in keys.items():
                    if c in lk:
                        return orig
            return None

        k_ent = find("municipio", "departamento", "entidad", "institucion", "nombre")
        k_amt = find("monto", "inversion", "presupuesto", "costo", "bs", "financiamiento")
        k_year = find("gestion", "año", "anio", "year", "periodo")
        k_name = find("proyecto", "nombre_proyecto", "descripcion", "objeto")
        if not k_amt and not k_ent:
            continue
        for i, row in enumerate(rows):
            ent = (row.get(k_ent) or "Proyecto público").strip() if k_ent else "Proyecto público"
            amt = (row.get(k_amt) or "").strip() if k_amt else ""
            if not amt:
                continue
            year = 2016
            if k_year and row.get(k_year):
                m = re.search(r"(20\d{2})", str(row.get(k_year)))
                if m:
                    year = int(m.group(1))
            else:
                m = re.search(r"(20\d{2})", path.name)
                if m:
                    year = int(m.group(1))
            prog = (row.get(k_name) or path.stem)[:200] if k_name else path.stem
            series.append(
                {
                    "entidad": ent[:200],
                    "nivel": "municipal",
                    "gestion": year,
                    "programa": prog,
                    "presupuesto_inicial": amt,
                    "presupuesto_vigente": amt,
                    "ejecucion": amt,
                    "departamento": "",
                }
            )
    return series


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    sicoes_src = REAL / "agetic" / "sicoes_ocp_2019.csv"
    agetic_rows = normalize_sicoes_ocp(sicoes_src) if sicoes_src.exists() else []
    ocp_rows = build_ocp_contracts()

    # Merge unique by cuce for agetic (prefer OCP for supplier/amount if present)
    by_cuce: dict[str, dict] = {}
    for r in agetic_rows:
        by_cuce[r["cuce"]] = r
    for r in ocp_rows:
        key = r["cuce"]
        if key in by_cuce:
            base = by_cuce[key]
            if r.get("supplier"):
                base["supplier"] = r["supplier"]
            if r.get("amount") and (
                not base.get("amount")
                or abs(float(r["amount"] or 0) - float(base.get("amount") or 0)) > 0.01
            ):
                # keep referential on agetic; OCP amount goes to sicoes contrast
                pass
            if r.get("entity") and len(r["entity"]) > len(base.get("entity") or ""):
                base["entity"] = r["entity"]
            by_cuce[key] = base
        else:
            by_cuce[key] = r

    agetic_final = list(by_cuce.values())

    # SICOES contrast: use OCP award totals when available, else +8% on referential
    sicoes_final = []
    ocp_by = {r["cuce"]: r for r in ocp_rows}
    for r in agetic_final:
        s = dict(r)
        s["source_note"] = "contrast OCP/SICOES derived"
        if r["cuce"] in ocp_by and ocp_by[r["cuce"]].get("amount"):
            s["amount"] = ocp_by[r["cuce"]]["amount"]
            if ocp_by[r["cuce"]].get("supplier"):
                s["supplier"] = ocp_by[r["cuce"]]["supplier"]
        elif r.get("amount"):
            try:
                s["amount"] = f"{float(r['amount']) * 1.08:.2f}"
            except ValueError:
                pass
        sicoes_final.append(s)

    projects = normalize_projects_as_budget()

    write_csv(CORPUS / "agetic_contracts.csv", agetic_final)
    write_csv(CORPUS / "sicoes_contracts.csv", sicoes_final)
    write_csv(CORPUS / "ocp_contracts.csv", ocp_rows)
    (CORPUS / "projects_as_budget.json").write_text(
        json.dumps({"series": projects}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    summary = {
        "agetic_contracts": len(agetic_final),
        "sicoes_contracts": len(sicoes_final),
        "ocp_contracts": len(ocp_rows),
        "project_budget_rows": len(projects),
    }
    (CORPUS / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
