"""Smoke tests for F13 fire alert rules (no DB required for helpers)."""
from __future__ import annotations

from decimal import Decimal


def test_alerts_module_importable():
    from worker.alerts_fire import run_fire_alert_rules

    assert callable(run_fire_alert_rules)


def test_synthetic_amount_helper_logic():
    """Mirror of _amt exclusion used by alert rules."""

    class Row:
        is_synthetic = True
        ledger_bucket = "sintetico"
        amount_attributed = Decimal("12500000")

    # Inline the same guard as alerts_fire._amt
    if getattr(Row(), "is_synthetic", False) or getattr(Row(), "ledger_bucket", None) == "sintetico":
        amt = Decimal("0")
    else:
        amt = Row().amount_attributed or Decimal("0")
    assert amt == Decimal("0")
