#!/usr/bin/env python3
"""
Extract fire/VIDECI/budget evidence from ALL downloaded official PDFs (multi-year).
Output: data/extracted/fire_multi_year_raw.json
"""
from __future__ import annotations

import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "extracted"
OUT.mkdir(parents=True, exist_ok=True)

FIRE_RE = re.compile(
    r"(incendio|forestal|VIDECI|aeronave|helic[oó]ptero|bombero|Guardian|"
    r"fuego|quemad|chaqueo|CCREA|brigada|mitigad|sofocad|"
    r"gesti[oó]n\s+del\s+fuego|focos?\s+de\s+calor)",
    re.I,
)
MONEY_RE = re.compile(
    r"Bs\.?\s*([\d\.]+(?:,\d+)?(?:\.\d+)?)\s*(?:millones?)?|"
    r"([\d\.]+)\s*millones?\s*(?:de\s*)?bolivianos?",
    re.I,
)
YEAR_IN_NAME = re.compile(r"(20\d{2})")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def guess_year(path: Path) -> int | None:
    m = YEAR_IN_NAME.search(path.name)
    return int(m.group(1)) if m else None


def extract_pdf(path: Path, max_pages: int | None = None) -> dict:
    """Full-text scan for fire pages + budget totals."""
    fire_pages: list[dict] = []
    budget_hits: list[dict] = []
    metrics_candidates: list[dict] = []
    page_count = 0
    try:
        with pdfplumber.open(path) as pdf:
            page_count = len(pdf.pages)
            pages = pdf.pages[:max_pages] if max_pages else pdf.pages
            for i, page in enumerate(pages, start=1):
                text = page.extract_text() or ""
                if not text.strip():
                    continue
                # Budget institutional totals
                if re.search(r"presupuesto\s+(vigente|institucional)|ejecuci[oó]n\s+alcanz", text, re.I):
                    for line in text.splitlines():
                        if re.search(r"Bs\.?\s*[\d\.]+|TOTAL|ejecut", line, re.I):
                            if len(line.strip()) > 15:
                                budget_hits.append({"page": i, "line": line.strip()[:300]})
                if not FIRE_RE.search(text):
                    continue
                # Keep fire page text (trimmed)
                fire_pages.append({"page": i, "text": text[:5000], "chars": len(text)})
                # Metric-like lines
                for line in text.splitlines():
                    if FIRE_RE.search(line) and re.search(r"\d", line):
                        metrics_candidates.append({"page": i, "line": line.strip()[:400]})
    except Exception as e:
        return {
            "path": str(path.relative_to(ROOT)),
            "error": f"{type(e).__name__}: {e}",
            "sha256": sha256(path) if path.exists() else None,
        }

    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "pages": page_count,
        "year_guess": guess_year(path),
        "source": path.parent.name,
        "fire_page_count": len(fire_pages),
        "fire_pages": fire_pages[:40],
        "metric_lines": metrics_candidates[:80],
        "budget_lines": budget_hits[:40],
    }


def main() -> None:
    pdfs = [p for p in sorted(RAW.rglob("*.pdf")) if p.stat().st_size > 5_000]
    print(f"Scanning {len(pdfs)} PDFs…")
    results = []
    # SERNAP 2024 is 20MB — cap pages for speed but still get fire content
    caps = {
        "sernap/rpc_final_2024.pdf": 60,
        "sernap/rpc_inicial_2025.pdf": 50,
        "mindef/rpc_final_2025.pdf": 80,
        "mindef/rpc_final_2022.pdf": None,
    }

    def job(p: Path) -> dict:
        rel = str(p.relative_to(RAW)).replace("\\", "/")
        cap = caps.get(rel)
        print(f"  {rel} cap={cap}")
        return extract_pdf(p, max_pages=cap)

    # Sequential is safer for memory with large PDFs
    for p in pdfs:
        results.append(job(p))

    out = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "pdf_count": len(results),
        "documents": results,
    }
    dest = OUT / "fire_multi_year_raw.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {dest} ({dest.stat().st_size} bytes)")
    for d in results:
        if d.get("error"):
            print(f"ERR {d['path']}: {d['error']}")
        else:
            print(
                f"OK {d['path']} y={d.get('year_guess')} pages={d.get('pages')} "
                f"fire_pages={d.get('fire_page_count')} metrics={len(d.get('metric_lines') or [])}"
            )


if __name__ == "__main__":
    main()
