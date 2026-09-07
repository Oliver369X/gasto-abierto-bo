"""Tests for fire rollup anti-double-count."""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from common.fire.rollup import build_rollup


def test_dedupes_same_cuce():
    rows = [
        SimpleNamespace(
            year=2024,
            cuce="24-1",
            contract_id=None,
            code="A",
            is_synthetic=False,
            ledger_bucket="verificable",
            attribution="directo",
            cycle="respuesta",
            amount_attributed=Decimal("100"),
            amount_attributed_base=Decimal("100"),
            amount_contract=Decimal("100"),
            budget_line_id=None,
        ),
        SimpleNamespace(
            year=2024,
            cuce="24-1",
            contract_id=None,
            code="B",
            is_synthetic=False,
            ledger_bucket="verificable",
            attribution="directo",
            cycle="respuesta",
            amount_attributed=Decimal("100"),
            amount_attributed_base=Decimal("100"),
            amount_contract=Decimal("100"),
            budget_line_id=None,
        ),
    ]
    out = build_rollup(rows, [])
    assert len(out) == 1
    assert out[0]["contratado_verificable"] == 100.0
    assert out[0]["unique_processes"] == 1


def test_skips_synthetic():
    rows = [
        SimpleNamespace(
            year=2024,
            cuce="x",
            contract_id=None,
            code="S",
            is_synthetic=True,
            ledger_bucket="sintetico",
            attribution="directo",
            cycle="respuesta",
            amount_attributed=Decimal("999"),
            amount_attributed_base=Decimal("999"),
            amount_contract=Decimal("999"),
            budget_line_id=None,
        )
    ]
    out = build_rollup(rows, [])
    assert out[0]["contratado_verificable"] == 0.0
