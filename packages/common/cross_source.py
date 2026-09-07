from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable

from common.cuce import normalize_cuce
from common.discrepancy import build_discrepancy, delta_pct


def match_key_cuce(cuce: str | None) -> str | None:
    return normalize_cuce(cuce)


def group_contracts_by_cuce(rows: Iterable[Any]) -> dict[str, list[Any]]:
    """Group ORM-like rows that expose ``.cuce`` and ``.source_id``."""
    groups: dict[str, list[Any]] = {}
    for row in rows:
        key = normalize_cuce(getattr(row, "cuce", None))
        if not key:
            continue
        groups.setdefault(key, []).append(row)
    return groups


def discrepancies_from_cuce_groups(
    groups: dict[str, list[Any]],
) -> list[dict[str, Any]]:
    """Emit amount mismatches across sources for the same normalized CUCE."""
    out: list[dict[str, Any]] = []
    for key, items in groups.items():
        by_source: dict[str, Any] = {}
        for item in items:
            sid = getattr(item, "source_id", None) or "unknown"
            # keep first current amount per source
            if sid not in by_source:
                by_source[sid] = item
        sources = list(by_source.keys())
        for i, sa in enumerate(sources):
            for sb in sources[i + 1 :]:
                a = by_source[sa]
                b = by_source[sb]
                disc = build_discrepancy(
                    concept=f"contract:{key}",
                    entity_id=getattr(a, "entity_id", None) or getattr(b, "entity_id", None),
                    amount_a=getattr(a, "amount", None),
                    amount_b=getattr(b, "amount", None),
                    source_a=sa,
                    source_b=sb,
                    ref_a=str(getattr(a, "id", "") or ""),
                    ref_b=str(getattr(b, "id", "") or key),
                )
                if disc:
                    disc["delta_pct"] = delta_pct(disc["amount_a"], disc["amount_b"])
                    out.append(disc)
    return out


def budget_vs_contracts_discrepancy(
    *,
    entity_id: int,
    year: int,
    budget_executed: Decimal | None,
    contracts_sum: Decimal | None,
    budget_source: str,
    contracts_source: str = "contracts_aggregate",
    tolerance_pct: Decimal = Decimal("15"),
) -> dict[str, Any] | None:
    """Flag when awarded contracts diverge sharply from executed budget.

    Not an exact accounting identity — useful citizen signal when Δ% > tolerance.
    """
    if budget_executed is None or contracts_sum is None:
        return None
    if budget_executed <= 0 and contracts_sum <= 0:
        return None
    pct = delta_pct(budget_executed, contracts_sum)
    if pct is None or Decimal(str(pct)) < tolerance_pct:
        return None
    disc = build_discrepancy(
        concept=f"budget_vs_contracts:{entity_id}:{year}",
        entity_id=entity_id,
        amount_a=budget_executed,
        amount_b=contracts_sum,
        source_a=budget_source,
        source_b=contracts_source,
        ref_a=f"budget:{year}",
        ref_b=f"contracts:{year}",
    )
    if disc:
        disc["delta_pct"] = pct
    return disc
