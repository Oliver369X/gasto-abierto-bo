#!/usr/bin/env python3
"""Extract fire-related evidence from downloaded official documents."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pdfplumber
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "extracted"
OUT.mkdir(parents=True, exist_ok=True)

FIRE_RE = re.compile(
    r"(incendio|forestal|chaqueo|quemad|VIDECI|bombero|aeronave|helic[oó]ptero|"
    r"cisterna|brigada|mitigad|desastre|emergencia|Chiquitania|Robor[eé]|"
    r"Concepci[oó]n|San Ignacio|hect[aá]rea)",
    re.I,
)
MONEY_RE = re.compile(
    r"(Bs\.?\s*[\d\.]+(?:\s*(?:millones?|MM))?|"
    r"[\d\.]+\s*(?:millones?\s+de\s+bolivianos)|"
    r"USD?\s*[\d\.,]+)",
    re.I,
)
NUM_RE = re.compile(r"[\d\.]+")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_pdf(path: Path) -> dict:
    pages_out = []
    hits = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            tables = []
            for t in page.extract_tables() or []:
                tables.append([[(c or "").strip() for c in row] for row in t])
            pages_out.append({"page": i, "chars": len(text), "tables": len(tables)})
            if FIRE_RE.search(text):
                # keep paragraphs with fire keywords
                for para in re.split(r"\n{2,}|\n(?=[A-ZÁÉÍÓÚ])", text):
                    if FIRE_RE.search(para) and len(para.strip()) > 40:
                        hits.append(
                            {
                                "page": i,
                                "text": para.strip()[:1200],
                                "money": MONEY_RE.findall(para)[:8],
                            }
                        )
                for ti, table in enumerate(tables):
                    flat = " | ".join(" ".join(row) for row in table)
                    if FIRE_RE.search(flat):
                        hits.append(
                            {
                                "page": i,
                                "table_index": ti,
                                "table_preview": table[:12],
                                "money": MONEY_RE.findall(flat)[:12],
                            }
                        )
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256_file(path),
        "pages": len(pages_out),
        "page_stats": pages_out,
        "fire_hits": hits[:200],
        "hit_count": len(hits),
    }


def extract_html_links(path: Path) -> dict:
    html = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        label = " ".join(a.get_text(" ", strip=True).split())[:200]
        if not href:
            continue
        low = href.lower()
        blob = f"{label} {href}"
        if any(x in low for x in (".pdf", ".xlsx", ".xls", ".csv", "wp-content/uploads")) or FIRE_RE.search(
            blob
        ):
            links.append({"href": href, "label": label})
    # dedupe
    seen = set()
    uniq = []
    for L in links:
        if L["href"] in seen:
            continue
        seen.add(L["href"])
        uniq.append(L)
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256_file(path),
        "links": uniq[:300],
        "link_count": len(uniq),
        "title": (soup.title.string if soup.title else "") or "",
    }


def main() -> None:
    report: dict = {"documents": [], "html_indexes": []}
    pdf = RAW / "mindef" / "rpc_final_2024.pdf"
    if pdf.exists():
        print("Extracting MINDEF RPC PDF…")
        doc = extract_pdf(pdf)
        report["documents"].append(doc)
        (OUT / "mindef_rpc_2024_hits.json").write_text(
            json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  pages={doc['pages']} fire_hits={doc['hit_count']} sha={doc['sha256'][:16]}")

    for html in RAW.rglob("*.html"):
        print(f"Parsing links {html.relative_to(ROOT)}…")
        idx = extract_html_links(html)
        report["html_indexes"].append(idx)
        print(f"  links={idx['link_count']}")

    (OUT / "source_harvest_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Wrote data/extracted/source_harvest_report.json")


if __name__ == "__main__":
    main()
