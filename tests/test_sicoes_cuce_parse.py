"""B1 — parse SICOES CUCE ficha HTML without network."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from worker.adapters.sicoes import parse_cuce_html

FIXTURE = Path(__file__).parent / "fixtures" / "sicoes" / "ficha_sample.html"
CUCE = "24-0123-00-1234567-1-1"


def test_parse_cuce_html_extracts_spanish_labels() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    detail = parse_cuce_html(html, cuce=CUCE)

    assert detail["cuce"] == CUCE
    assert detail["supplier_name"] == "Constructora Andes S.R.L."
    assert detail["nit"] == "123456789"
    assert detail["reference_price"] == Decimal("1250000.00")
    assert detail["amount"] == Decimal("1180500.50")
    assert "html" in detail


def test_parse_cuce_html_partial_labels() -> None:
    html = "<html><body><p>Proveedor: Solo Proveedor SA</p><p>NIT: 987654321</p></body></html>"
    detail = parse_cuce_html(html, cuce="x")
    assert detail["supplier_name"] == "Solo Proveedor SA"
    assert detail["nit"] == "987654321"
    assert "amount" not in detail or detail.get("amount") is None
