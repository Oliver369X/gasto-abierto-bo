#!/usr/bin/env python3
"""Normalize ALL monthly SICOES history into per-year corpus CSVs (streaming)."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HIST = ROOT / "tests" / "fixtures" / "real" / "sicoes_history"
CORPUS = ROOT / "tests" / "fixtures" / "real" / "corpus" / "by_year"
CORPUS.mkdir(parents=True, exist_ok=True)

FIELDS = [
    "cuce",
    "entity",
    "supplier",
    "description",
    "amount",
    "modality",
    "date",
    "status",
    "department",
    "source_note",
]


def _year_from(cuce: str, date: str, yyyymm: str | None) -> int:
    m = re.search(r"(20\d{2}|19\d{2})", date or "")
    if m:
        return int(m.group(1))
    m = re.match(r"^(\d{2})-", cuce or "")
    if m:
        yy = int(m.group(1))
        return 2000 + yy if yy < 80 else 1900 + yy
    if yyyymm and len(yyyymm) >= 4:
        return int(yyyymm[:4])
    return 0


def normalize_row(row: dict, *, source_note: str, yyyymm: str | None = None) -> tuple[int, dict] | None:
    lower = {(k or "").lower().strip(): v for k, v in row.items() if k}

    def g(*names: str) -> str:
        for n in names:
            if n in lower and lower[n] not in (None, ""):
                return str(lower[n]).strip()
        return ""

    cuce = g("cuce")
    entity = g("entidad", "entity", "nombre_entidad")
    if not cuce or not entity:
        return None
    date = g("fecha_publicacion", "fecha_presentacion", "date")
    amount = g("monto", "amount", "precio")
    if amount.upper() in ("NA", "N/A", "-", ""):
        amount = ""
    year = _year_from(cuce, date, yyyymm)
    if year < 2005 or year > 2030:
        return None
    return year, {
        "cuce": cuce,
        "entity": entity,
        "supplier": g("proveedor", "supplier"),
        "description": g("objeto_de_contratacion", "objeto", "description"),
        "amount": amount,
        "modality": g("modalidad", "modality"),
        "date": date[:10] if date else "",
        "status": g("estado", "status"),
        "department": g("departamento", "department"),
        "source_note": source_note,
    }


def main() -> None:
    # Clear previous year files
    for old in CORPUS.glob("sicoes_*.csv"):
        old.unlink()

    writers: dict[int, csv.DictWriter] = {}
    handles: dict[int, object] = {}
    seen: dict[int, set[str]] = {}
    counts: dict[int, int] = {}

    def writer_for(year: int) -> csv.DictWriter:
        if year not in writers:
            path = CORPUS / f"sicoes_{year}.csv"
            fh = path.open("w", encoding="utf-8", newline="")
            handles[year] = fh
            w = csv.DictWriter(fh, fieldnames=FIELDS)
            w.writeheader()
            writers[year] = w
            seen[year] = set()
            counts[year] = 0
        return writers[year]

    def consume(path: Path, source_note: str, yyyymm: str | None = None) -> int:
        n = 0
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                parsed = normalize_row(row, source_note=source_note, yyyymm=yyyymm)
                if not parsed:
                    continue
                year, rec = parsed
                if rec["cuce"] in seen[year] if year in seen else False:
                    # update: skip first-seen wins for speed
                    continue
                w = writer_for(year)
                if rec["cuce"] in seen[year]:
                    continue
                seen[year].add(rec["cuce"])
                w.writerow(rec)
                counts[year] += 1
                n += 1
        return n

    months = sorted((HIST / "months").glob("*.csv")) if (HIST / "months").exists() else []
    print(f"monthly files: {len(months)}")
    for i, path in enumerate(months, 1):
        n = consume(path, f"sociedatos/{path.stem}", path.stem)
        if i % 24 == 0:
            print(f"  processed {i}/{len(months)} (+{n} last)")

    lab = HIST / "lab_todo.csv"
    if lab.exists():
        print("merging lab todo…")
        consume(lab, "lab-tecnosocial/todo")

    for fh in handles.values():
        fh.close()

    summary = {
        "years": {str(y): counts[y] for y in sorted(counts)},
        "year_count": len(counts),
        "total_contracts": sum(counts.values()),
        "year_min": min(counts) if counts else None,
        "year_max": max(counts) if counts else None,
    }
    (CORPUS / "years_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    if summary["year_count"] < 10:
        raise SystemExit("expected many gestiones/years")
    if summary["total_contracts"] < 50_000:
        raise SystemExit(f"expected large history, got {summary['total_contracts']}")


if __name__ == "__main__":
    main()
