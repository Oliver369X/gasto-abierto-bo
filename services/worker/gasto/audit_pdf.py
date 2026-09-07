"""B5 — CGE / audit PDF finding extraction."""
from __future__ import annotations

import hashlib
import re
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from common.claims import ensure_raw_artifact
from common.money import parse_money
from schema.models import AuditFinding

# Lines that look like numbered findings / observations
_FINDING_LINE = re.compile(
    r"(?i)^\s*(?:hallazgo|observaci[oó]n|recomendaci[oó]n|deficiencia|"
    r"incumplimiento)?\s*[#:]?\s*(\d+[.)]|[-•])?\s*(.+)$"
)
_AMOUNT = re.compile(
    r"(?i)(?:bs\.?|bob)\s*([\d]{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?|\d+[.,]\d{2})"
)
_AMOUNT_FALLBACK = re.compile(
    r"(?i)(?:monto|importe|por)\s+(?:de\s+)?(?:bs\.?|bob)?\s*"
    r"([\d]{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?|\d+[.,]\d{2})"
)


def extract_findings_from_text(text: str) -> list[dict[str, Any]]:
    """Parse findings from plain text (HTML/PDF extract or fixtures)."""
    findings: list[dict[str, Any]] = []
    if not (text or "").strip():
        return findings
    for raw_line in text.replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if len(line) < 12:
            continue
        lower = line.lower()
        if not any(
            k in lower
            for k in (
                "hallazgo",
                "observaci",
                "recomend",
                "deficien",
                "incumpl",
                "observación",
            )
        ):
            # Still accept long numbered bullets as findings
            if not re.match(r"^\d+[.)]\s+\S", line):
                continue
        title = line[:200]
        amount = None
        m_amt = _AMOUNT.search(line) or _AMOUNT_FALLBACK.search(line)
        if m_amt:
            amount = parse_money(m_amt.group(1))
        severity = "medium"
        if any(k in lower for k in ("grave", "alto", "crític", "critic")):
            severity = "high"
        elif any(k in lower for k in ("leve", "bajo", "menor")):
            severity = "low"
        findings.append(
            {
                "title": title,
                "description": line,
                "severity": severity,
                "amount": amount,
                "evidence": {"quote": line[:500]},
            }
        )
    return findings


def extract_findings(pdf_bytes: bytes) -> list[dict[str, Any]]:
    """Extract findings from PDF bytes via pdfplumber; soft-fail needs_ocr."""
    if not pdf_bytes:
        return [{"title": "empty_pdf", "needs_ocr": True, "description": "No bytes"}]
    try:
        import pdfplumber
    except ImportError:
        return [
            {
                "title": "pdfplumber_unavailable",
                "needs_ocr": True,
                "description": "pdfplumber not installed",
            }
        ]
    try:
        pages_text: list[str] = []
        import io

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                pages_text.append(page.extract_text() or "")
        text = "\n".join(pages_text)
        if not text.strip():
            return [
                {
                    "title": "needs_ocr",
                    "needs_ocr": True,
                    "description": "No extractable text; OCR required",
                }
            ]
        findings = extract_findings_from_text(text)
        if not findings:
            # Fallback: one finding per non-empty page chunk
            for i, chunk in enumerate(pages_text):
                chunk = chunk.strip()
                if chunk:
                    findings.append(
                        {
                            "title": f"Página {i + 1}",
                            "description": chunk[:2000],
                            "severity": "medium",
                            "evidence": {"page": i + 1},
                        }
                    )
        return findings
    except Exception as exc:  # noqa: BLE001
        return [
            {
                "title": "extract_error",
                "needs_ocr": True,
                "description": str(exc),
            }
        ]


def persist_findings(
    session: Session,
    audit_id: int,
    findings: list[dict[str, Any]],
    sha256: str,
    url: str,
) -> int:
    """Persist AuditFinding rows + raw artifact for the PDF/source."""
    art = ensure_raw_artifact(
        session,
        url=url,
        sha256=sha256,
        source_id="cge",
        mime="application/pdf",
        meta={"audit_report_id": audit_id},
    )
    n = 0
    for f in findings:
        if f.get("needs_ocr") and f.get("title") in (
            "needs_ocr",
            "pdfplumber_unavailable",
            "empty_pdf",
            "extract_error",
        ):
            continue
        amt = f.get("amount")
        if amt is not None and not isinstance(amt, Decimal):
            amt = parse_money(str(amt))
        evidence = dict(f.get("evidence") or {})
        evidence.setdefault("url", url)
        evidence.setdefault("sha256", sha256)
        evidence.setdefault("raw_artifact_id", art.id)
        session.add(
            AuditFinding(
                audit_report_id=audit_id,
                title=str(f.get("title") or "Hallazgo")[:1024],
                description=f.get("description"),
                severity=f.get("severity") or "medium",
                amount=amt,
                evidence=evidence,
            )
        )
        n += 1
    session.flush()
    return n


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
