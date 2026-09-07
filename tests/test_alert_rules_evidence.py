"""B8 — unit tests for evidence alert rule filters (no DB)."""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from worker.alerts import (
    MISSING_NIT_AMOUNT_THRESHOLD,
    filter_amount_claim_conflicts,
    filter_missing_nit_high_amount,
)


def test_filter_missing_nit_high_amount() -> None:
    high_no_nit = SimpleNamespace(
        is_synthetic=False,
        amount=MISSING_NIT_AMOUNT_THRESHOLD,
        supplier_id=1,
        supplier=SimpleNamespace(nit=None, is_synthetic=False),
    )
    high_with_nit = SimpleNamespace(
        is_synthetic=False,
        amount=Decimal("900000"),
        supplier_id=2,
        supplier=SimpleNamespace(nit="123", is_synthetic=False),
    )
    low = SimpleNamespace(
        is_synthetic=False,
        amount=Decimal("1000"),
        supplier_id=3,
        supplier=SimpleNamespace(nit=None, is_synthetic=False),
    )
    synthetic = SimpleNamespace(
        is_synthetic=True,
        amount=Decimal("900000"),
        supplier_id=4,
        supplier=SimpleNamespace(nit=None, is_synthetic=False),
    )
    out = filter_missing_nit_high_amount([high_no_nit, high_with_nit, low, synthetic])
    assert out == [high_no_nit]


def test_filter_amount_claim_conflicts() -> None:
    open_amt = SimpleNamespace(status="open", field="amount", is_synthetic=False)
    closed = SimpleNamespace(status="resolved", field="amount", is_synthetic=False)
    other_field = SimpleNamespace(status="open", field="nit", is_synthetic=False)
    out = filter_amount_claim_conflicts([open_amt, closed, other_field])
    assert out == [open_amt]
