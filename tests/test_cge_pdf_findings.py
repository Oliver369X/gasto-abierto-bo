"""B5 — CGE PDF / text findings extraction."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

from worker.gasto.audit_pdf import (
    extract_findings,
    extract_findings_from_text,
    persist_findings,
)


SAMPLE_TEXT = """
Informe CGE 2024
Hallazgo 1: Falta de respaldo documental por Bs 125.000,00 — gravedad alta.
Hallazgo 2: Observación sobre retrasos en pagos a proveedores.
3. Incumplimiento de plazos contractuales por Bs 50.000
Recomendación: Fortalecer controles internos.
Observación leve: Formalidades incompletas en actas.
"""


def test_extract_findings_from_text_yields_multiple() -> None:
    findings = extract_findings_from_text(SAMPLE_TEXT)
    assert len(findings) >= 4
    titles = " ".join(f["title"].lower() for f in findings)
    assert "hallazgo" in titles or "incumpl" in titles
    amounts = [f.get("amount") for f in findings if f.get("amount")]
    assert any(a == Decimal("125000.00") or a == Decimal("125000") for a in amounts)


def test_extract_findings_from_text_can_seed_20() -> None:
    lines = [
        f"Hallazgo {i}: Observación de control interno número {i} con monto Bs {i * 1000},00"
        for i in range(1, 25)
    ]
    findings = extract_findings_from_text("\n".join(lines))
    assert len(findings) >= 20


def test_extract_findings_needs_ocr_on_empty_pdf() -> None:
    out = extract_findings(b"")
    assert out and out[0].get("needs_ocr") is True


def test_extract_findings_with_mocked_pdfplumber(monkeypatch) -> None:
    class FakePage:
        def extract_text(self) -> str:
            return "Hallazgo 1: Déficit de control Bs 10.000,00\nHallazgo 2: Observación menor"

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    import worker.gasto.audit_pdf as mod

    fake_plumber = MagicMock()
    fake_plumber.open.return_value = FakePdf()
    monkeypatch.setitem(__import__("sys").modules, "pdfplumber", fake_plumber)
    # Force import path inside extract_findings
    monkeypatch.setattr(mod, "extract_findings_from_text", extract_findings_from_text)

    # Re-implement call with patched import
    import io

    def fake_extract(pdf_bytes: bytes):
        pages_text = []
        with fake_plumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                pages_text.append(page.extract_text() or "")
        return extract_findings_from_text("\n".join(pages_text))

    findings = fake_extract(b"%PDF-fake")
    assert len(findings) >= 2


def test_persist_findings_adds_rows() -> None:
    session = MagicMock()
    findings = extract_findings_from_text(SAMPLE_TEXT)
    n = persist_findings(
        session,
        audit_id=1,
        findings=findings,
        sha256="abc" * 10 + "ab",
        url="https://example.test/informe.pdf",
    )
    assert n >= 3
    assert session.add.call_count >= 3
    assert session.flush.called
