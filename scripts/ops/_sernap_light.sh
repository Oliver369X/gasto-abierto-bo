#!/bin/sh
# Light SERNAP extract against existing manifest (no full re-catalog).
set -e
export PYTHONPATH=/app/packages:/app/services:/app
export SERNAP_OCR_MAX_PAGES="${SERNAP_OCR_MAX_PAGES:-5}"
export SERNAP_EXTRACT_MAX_DOCS="${SERNAP_EXTRACT_MAX_DOCS:-3}"
python - <<'PY'
from worker.fire.context import get_session
from worker.fire.phases.f03_corpus import (
    extract_sernap_text_pages,
    ocr_sernap_scans,
    persist_sernap_outputs,
)
from worker.fire.artifacts import write_json

extract = extract_sernap_text_pages()
ocr = ocr_sernap_scans()
write_json(
    "f03_sernap_text.json",
    {
        "status": extract.get("status"),
        "pages_extracted": extract.get("extracted", 0),
        "pages": extract.get("pages") or [],
    },
)
pages = ocr.get("pages") or []
write_json(
    "f03_sernap_ocr.json",
    {
        "status": ocr.get("status"),
        "ocr_ok": sum(1 for p in pages if p.get("status") == "ocr"),
        "ocr_failed": sum(
            1 for p in pages if p.get("status") in {"ocr_error", "ocr_unavailable", "error"}
        ),
        "pages": pages,
    },
)
session = get_session()
try:
    persist = persist_sernap_outputs(session)
    session.commit()
finally:
    session.close()
print(
    {
        "extract": extract.get("extracted"),
        "ocr_status": ocr.get("status"),
        "ocr_pages": len(pages),
        "persist": persist,
    }
)
PY
