"""F3: catalogue PDFs, parse MINDEF evidence, and version text extracts."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber
from sqlalchemy import select

from schema.models import OperationalOutput
from worker.fire.artifacts import extracted_root, write_json

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / "data" / "raw"
FIRE_RE = re.compile(r"incendio|focos?\s+de\s+calor|aeronave|helic[oó]ptero|brigad|bombero\s+forestal|guardian|bambi|hect[aá]reas?\s+quemad|sofocaci[oó]n|VIDECI", re.I)
NUMBER_UNIT_RE = re.compile(
    r"(?P<number>\d[\d\s.,]*)\s*(?P<unit>hect[aá]reas?|ha\b|Bs\.?|BOB\b)",
    re.I,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify_page(text: str, has_table: bool, chars: int) -> str:
    if chars < 40:
        return "image_or_scan"
    if has_table:
        return "table"
    if re.search(r"mapa|map\b|leyenda", text, re.I):
        return "map"
    if re.search(r"gr[aá]fico|figura\s+\d", text, re.I):
        return "chart"
    return "text"


def catalog_pdf(path: Path, max_pages: int = 80) -> dict:
    try:
        with pdfplumber.open(path) as pdf:
            pages = []
            total = len(pdf.pages)
            for number, page in enumerate(pdf.pages[:max_pages], 1):
                text, tables = page.extract_text() or "", page.extract_tables() or []
                pages.append({"page": number, "chars": len(text),
                              "type": classify_page(text, bool(tables), len(text)),
                              "tables": len(tables)})
        return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path),
                "bytes": path.stat().st_size, "pages_total": total,
                "pages_sampled": len(pages), "page_types": pages}
    except Exception as exc:
        return {"path": path.relative_to(ROOT).as_posix(), "error": str(exc)}


def catalog(*, write_artifact: bool = True) -> dict:
    docs = [catalog_pdf(pdf, 40 if "sernap" in pdf.as_posix().lower() else 80)
            for pdf in sorted(RAW.rglob("*.pdf")) if pdf.stat().st_size >= 5000]
    payload = {"built_at": datetime.now(timezone.utc).isoformat(), "version": "corpus_v1",
               "document_count": len(docs), "documents": docs}
    if write_artifact:
        write_json("manifest.json", payload, subdir="corpus_v1")
    return payload


def parse_mindef_pdf(path: Path, max_pages: int = 60) -> dict:
    hits, table_count = [], 0
    try:
        with pdfplumber.open(path) as pdf:
            total = len(pdf.pages)
            for number, page in enumerate(pdf.pages[:max_pages], 1):
                text = page.extract_text() or ""
                match = FIRE_RE.search(text)
                if not match:
                    continue
                tables = page.extract_tables() or []
                table_count += len(tables)
                span = re.sub(r"\s+", " ", text[max(0, match.start()-80):match.end()+200]).strip()
                hits.append({"page": number, "chars": len(text), "tables_on_page": len(tables),
                             "evidence_span": span[:400]})
        return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path),
                "pages_total": total, "fire_pages": len(hits),
                "tables_on_fire_pages": table_count, "hits": hits[:40]}
    except Exception as exc:
        return {"path": str(path), "error": str(exc)}


def parse_mindef(*, write_artifact: bool = True) -> dict:
    directory = RAW / "mindef"
    paths = sorted(directory.glob("*.pdf")) if directory.exists() else []
    docs = [parse_mindef_pdf(path) for path in paths if path.stat().st_size >= 5000]
    payload = {"status": "ok", "documents": docs, "parsed": len(docs),
               "with_fire_pages": sum(bool(doc.get("fire_pages")) for doc in docs),
               "sernap_note": "SERNAP remains catalogued; OCR deferred for scan-heavy pages"}
    if write_artifact:
        write_json("mindef_structured.json", payload, subdir="corpus_v1")
    return payload


def version_extracts(*, write_artifact: bool = True) -> dict:
    source, out = extracted_root(), extracted_root() / "corpus_v1" / "extracts"
    copies = [("mindef_rpc_2024_fire_pages.txt", "mindef/rpc_2024_fire_pages.txt"),
              ("fire_pages_by_year", "mindef/by_year")]
    copied = []
    if write_artifact:
        for source_name, destination_name in copies:
            src, destination = source / source_name, out / destination_name
            if not src.exists():
                continue
            if src.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                for file in src.glob("*.txt"):
                    shutil.copy2(file, destination / file.name)
                    copied.append((destination / file.name).relative_to(ROOT).as_posix())
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, destination)
                copied.append(destination.relative_to(ROOT).as_posix())
        write_json("README.json", {"copied": copied, "sernap": "catalogued; OCR deferred"},
                   subdir="corpus_v1/extracts")
    return {"status": "ok", "copied": copied, "count": len(copied)}


def _sernap_documents(manifest_path: Path) -> list[dict]:
    if not manifest_path.exists():
        return []
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return [
        doc for doc in data.get("documents", [])
        if "sernap" in str(doc.get("path", "")).lower() and not doc.get("error")
    ]


def extract_sernap_text_pages(
    *,
    manifest_path: Path | None = None,
    root: Path = ROOT,
    output_root: Path | None = None,
) -> dict:
    """Extract only manifest pages classified as text or table."""
    manifest_path = manifest_path or extracted_root() / "corpus_v1" / "manifest.json"
    output_root = output_root or extracted_root() / "corpus_v2" / "sernap"
    max_docs = int(os.getenv("SERNAP_EXTRACT_MAX_DOCS", "0") or "0")
    pages: list[dict] = []
    docs = _sernap_documents(manifest_path)
    if max_docs > 0:
        docs = docs[:max_docs]
    for doc in docs:
        path = root / doc["path"]
        sha = doc.get("sha256") or (sha256(path) if path.exists() else "unknown")
        wanted = {
            int(page["page"]) for page in doc.get("page_types", [])
            if page.get("type") in {"text", "table"}
        }
        if not wanted:
            continue
        try:
            with pdfplumber.open(path) as pdf:
                for number in sorted(wanted):
                    try:
                        text = pdf.pages[number - 1].extract_text() or ""
                        destination = output_root / sha / f"page_{number}.txt"
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_text(text, encoding="utf-8")
                        destination.with_suffix(".source").write_text(
                            "sernap_pdf", encoding="utf-8"
                        )
                        pages.append(
                            {"sha256": sha, "page": number, "status": "extracted",
                             "path": destination.as_posix()}
                        )
                    except Exception as exc:  # one bad page must not abort the document
                        pages.append({"sha256": sha, "page": number, "status": "error",
                                      "error": str(exc)})
        except Exception as exc:
            pages.append({"sha256": sha, "page": None, "status": "error", "error": str(exc)})
    return {"status": "ok", "extracted": sum(p["status"] == "extracted" for p in pages),
            "pages": pages}


def _load_ocr():
    try:
        import pytesseract
    except (ImportError, OSError):
        return None
    return pytesseract


def ocr_sernap_scans(
    *,
    manifest_path: Path | None = None,
    root: Path = ROOT,
    output_root: Path | None = None,
    max_pages: int | None = None,
) -> dict:
    """OCR scan pages with a hard cap and per-page soft failures."""
    manifest_path = manifest_path or extracted_root() / "corpus_v1" / "manifest.json"
    output_root = output_root or extracted_root() / "corpus_v2" / "sernap"
    cap = max_pages if max_pages is not None else int(os.getenv("SERNAP_OCR_MAX_PAGES", "15"))
    candidates: list[tuple[dict, int]] = []
    for doc in _sernap_documents(manifest_path):
        candidates.extend(
            (doc, int(page["page"])) for page in doc.get("page_types", [])
            if page.get("type") == "image_or_scan"
        )
    candidates = candidates[:max(0, cap)]
    ocr = _load_ocr()
    if ocr is None:
        pages = [{"sha256": doc.get("sha256", "unknown"), "page": number,
                  "status": "ocr_unavailable"} for doc, number in candidates]
        return {"status": "ocr_unavailable", "ocr": 0, "pages": pages}

    pages: list[dict] = []
    for doc, number in candidates:
        sha = doc.get("sha256", "unknown")
        try:
            with pdfplumber.open(root / doc["path"]) as pdf:
                image = pdf.pages[number - 1].to_image(resolution=200).original
                text = ocr.image_to_string(image, lang="spa")
            destination = output_root / sha / f"page_{number}.txt"
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(text, encoding="utf-8")
            destination.with_suffix(".source").write_text("sernap_ocr", encoding="utf-8")
            pages.append({"sha256": sha, "page": number, "status": "ocr",
                          "path": destination.as_posix()})
        except Exception as exc:
            pages.append({"sha256": sha, "page": number, "status": "ocr_error",
                          "error": str(exc)})
    return {"status": "ok", "ocr": sum(p["status"] == "ocr" for p in pages), "pages": pages}


def _clear_numeric(text: str) -> tuple[Decimal | None, str | None]:
    match = NUMBER_UNIT_RE.search(text)
    if not match:
        return None, None
    raw = re.sub(r"\s", "", match.group("number"))
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", ".")
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return None, None
    unit = match.group("unit").lower()
    return value, ("hectáreas" if unit.startswith(("hect", "ha")) else "BOB")


def persist_sernap_outputs(session, *, output_root: Path | None = None) -> dict:
    """Persist extracted evidence without inventing numeric values."""
    output_root = output_root or extracted_root() / "corpus_v2" / "sernap"
    persisted = 0
    for path in sorted(output_root.glob("*/page_*.txt")):
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            continue
        page = int(path.stem.removeprefix("page_"))
        provenance = path.with_suffix(".source")
        source_id = (
            provenance.read_text(encoding="utf-8").strip()
            if provenance.exists() else "sernap_pdf"
        )
        year_match = re.search(r"\b(20(?:1[0-9]|2[0-9]))\b", f"{path} {text}")
        year = int(year_match.group(1)) if year_match else 2024
        value, unit = _clear_numeric(text)
        metric_key = f"sernap_{path.parent.name[:12]}_p{page}"
        row = session.scalars(select(OperationalOutput).where(
            OperationalOutput.metric_key == metric_key,
            OperationalOutput.source_id == source_id,
        )).first()
        values = {
            "year": year, "metric_label": "Evidencia operativa SERNAP",
            "value_numeric": value, "value_text": text[:512], "unit": unit,
            "evidence_page": page, "evidence_quote": re.sub(r"\s+", " ", text)[:500],
            "source_id": source_id,
        }
        if row is None:
            session.add(OperationalOutput(metric_key=metric_key, **values))
        else:
            for key, item in values.items():
                setattr(row, key, item)
        persisted += 1
    session.flush()
    return {"status": "ok", "persisted": persisted}


def run(session=None, *, write_artifact: bool = True) -> dict:
    manifest = extracted_root() / "corpus_v1" / "manifest.json"
    force_catalog = os.getenv("FIRE_F3_FORCE_CATALOG", "").strip() in {"1", "true", "TRUE"}
    if manifest.exists() and not force_catalog:
        catalog_payload = {
            "status": "skipped",
            "note": "reuse existing corpus_v1/manifest.json (set FIRE_F3_FORCE_CATALOG=1 to rebuild)",
            "path": manifest.as_posix(),
        }
    else:
        catalog_payload = catalog(write_artifact=write_artifact)

    payload = {
        "status": "ok",
        "catalog": catalog_payload,
        "parse_mindef": parse_mindef(write_artifact=write_artifact),
        "version_extracts": version_extracts(write_artifact=write_artifact),
    }
    for name, operation in (
        ("sernap_extract", extract_sernap_text_pages),
        ("sernap_ocr", ocr_sernap_scans),
    ):
        try:
            payload[name] = operation()
        except Exception as exc:
            payload[name] = {"status": "error", "error": str(exc)}
    if write_artifact:
        extract = payload.get("sernap_extract") or {}
        ocr = payload.get("sernap_ocr") or {}
        ocr_pages = ocr.get("pages") or []
        write_json("f03_sernap_text.json", {
            "status": extract.get("status", "error"),
            "pages_extracted": extract.get("extracted", 0),
            "pages": extract.get("pages") or [],
        })
        write_json("f03_sernap_ocr.json", {
            "status": ocr.get("status", "error"),
            "ocr_ok": sum(1 for p in ocr_pages if p.get("status") == "ocr"),
            "ocr_failed": sum(
                1 for p in ocr_pages
                if p.get("status") in {"ocr_error", "ocr_unavailable", "error"}
            ),
            "pages": ocr_pages,
        })
    if session is not None:
        try:
            payload["sernap_persist"] = persist_sernap_outputs(session)
        except Exception as exc:
            payload["sernap_persist"] = {"status": "error", "error": str(exc)}
    return payload
