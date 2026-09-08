from __future__ import annotations

from decimal import Decimal
from typing import Any


def amounts_differ(a: Decimal | None, b: Decimal | None, *, tolerance: Decimal = Decimal("0.01")) -> bool:
    if a is None or b is None:
        return a != b
    return abs(a - b) > tolerance


def delta_pct(a: Decimal | None, b: Decimal | None) -> float | None:
    """Relative difference |a-b| / max(|a|,|b|) as percent."""
    if a is None or b is None:
        return None
    if a == 0 and b == 0:
        return 0.0
    if a == 0 or b == 0:
        return None
    base = max(abs(a), abs(b))
    if base == 0:
        return 0.0
    return float(abs(a - b) / base * 100)


def build_discrepancy(
    *,
    concept: str,
    entity_id: int | None,
    amount_a: Decimal | None,
    amount_b: Decimal | None,
    source_a: str,
    source_b: str,
    ref_a: str | None = None,
    ref_b: str | None = None,
) -> dict[str, Any] | None:
    if not amounts_differ(amount_a, amount_b):
        return None
    return {
        "concept": concept,
        "entity_id": entity_id,
        "amount_a": amount_a,
        "amount_b": amount_b,
        "source_a": source_a,
        "source_b": source_b,
        "ref_a": ref_a,
        "ref_b": ref_b,
    }
