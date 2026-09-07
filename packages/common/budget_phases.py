"""B6 — budget execution phases for display (never sum into one KPI)."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping


def _as_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:  # noqa: BLE001
        return None


def phases_for_display(row: Mapping[str, Any] | Any) -> dict[str, Any]:
    """Return budget phases as separate fields — do NOT sum into a single total.

    Consumers must treat initial / current / payment as distinct lifecycle stages.
    """

    def g(*keys: str) -> Any:
        if isinstance(row, Mapping):
            for k in keys:
                if k in row and row[k] is not None:
                    return row[k]
            return None
        for k in keys:
            if hasattr(row, k):
                v = getattr(row, k)
                if v is not None:
                    return v
        return None

    initial = _as_decimal(g("budget_initial", "initial_amount"))
    modification = _as_decimal(g("budget_modification", "modified_amount"))
    current = _as_decimal(g("budget_current", "current_amount"))
    commitment = _as_decimal(g("commitment"))
    accrual = _as_decimal(g("accrual"))
    payment = _as_decimal(g("payment", "executed_amount"))

    return {
        "budget_initial": initial,
        "budget_modification": modification,
        "budget_current": current,
        "commitment": commitment,
        "accrual": accrual,
        "payment": payment,
        "budget_phase": g("budget_phase") or "mapped",
        # Explicit: phases are NOT additive — callers must not sum them
        "do_not_sum": True,
        "note": (
            "Phases are lifecycle views (inicial → vigente → pagado). "
            "Never sum initial+current+payment as a total KPI."
        ),
    }
