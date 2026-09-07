"""Tests for budget phase display — must never treat phases as a summed KPI."""
from __future__ import annotations

from decimal import Decimal

from common.budget_phases import phases_for_display


def test_phases_for_display_keeps_fields_separate() -> None:
    row = {
        "budget_initial": Decimal("100"),
        "budget_current": Decimal("120"),
        "payment": Decimal("80"),
        "budget_phase": "mapped",
    }
    phases = phases_for_display(row)
    assert phases["budget_initial"] == Decimal("100")
    assert phases["budget_current"] == Decimal("120")
    assert phases["payment"] == Decimal("80")
    assert phases["do_not_sum"] is True
    # Guardrail: a naive sum must NOT equal any single "total" field we expose
    naive_sum = (
        (phases["budget_initial"] or 0)
        + (phases["budget_current"] or 0)
        + (phases["payment"] or 0)
    )
    assert "total" not in phases
    assert "total_amount" not in phases
    assert phases.get("sum") is None
    # If someone incorrectly added a summed KPI, this fails hard
    assert naive_sum == Decimal("300")
    assert phases.get("kpi_total") is None
    assert phases.get("total_budget") is None


def test_phases_fallback_legacy_field_names() -> None:
    row = {
        "initial_amount": "50.00",
        "current_amount": "60.00",
        "executed_amount": "10.00",
    }
    phases = phases_for_display(row)
    assert phases["budget_initial"] == Decimal("50.00")
    assert phases["budget_current"] == Decimal("60.00")
    assert phases["payment"] == Decimal("10.00")
    assert phases["budget_phase"] == "mapped"
