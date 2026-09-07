"""F1 gate: synthetic amounts must not enter direct verifiable totals."""
from __future__ import annotations

from decimal import Decimal

from common.fire.ledger import amount_for_public_kpi, is_public_verifiable


def test_synthetic_excluded_from_verifiable():
    class Row:
        is_synthetic = True
        ledger_bucket = "sintetico"
        quality_grade = "E"
        attribution = "directo"
        amount_attributed = Decimal("12500000")
        evidence = {"is_synthetic": True}

    assert is_public_verifiable(Row()) is False
    assert amount_for_public_kpi(Row()) == Decimal("0")


def test_quality_a_direct_included():
    class Row:
        is_synthetic = False
        ledger_bucket = "verificable"
        quality_grade = "A"
        attribution = "directo"
        amount_attributed = Decimal("870000")
        evidence = {}

    assert is_public_verifiable(Row()) is True
    assert amount_for_public_kpi(Row()) == Decimal("870000")


def test_no_relacionado_pool_excluded():
    class Row:
        is_synthetic = False
        ledger_bucket = "no_relacionado"
        quality_grade = "A"
        attribution = "no_relacionado"
        amount_attributed = None
        amount_contract = Decimal("116087763")
        evidence = {}

    assert is_public_verifiable(Row()) is False
    assert amount_for_public_kpi(Row()) == Decimal("0")
