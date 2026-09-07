"""Territorial coverage levels for ola 1 (SCZ / Beni / Pando)."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from common.fire.ledger import amount_for_public_kpi


def coverage_level(expenditure_count: int) -> str:
    if expenditure_count >= 10:
        return "Alta"
    if expenditure_count >= 3:
        return "Media"
    if expenditure_count >= 1:
        return "Baja"
    return "Sin datos"


OLA1_DEPARTMENTS: tuple[tuple[str, str], ...] = (
    ("santa-cruz", "Santa Cruz"),
    ("beni", "Beni"),
    ("pando", "Pando"),
)


def build_ola1_coverage(
    expenditures: list[Any],
    *,
    territories_by_slug: dict[str, Any],
) -> list[dict[str, Any]]:
    """Count non-synthetic expenditures per ola-1 department."""
    out: list[dict[str, Any]] = []
    for slug, name in OLA1_DEPARTMENTS:
        t = territories_by_slug.get(slug)
        if not t:
            out.append({
                "slug": slug,
                "name": name,
                "level": "Sin datos",
                "expenditures": 0,
                "amount_direct_verifiable": 0.0,
            })
            continue
        rows = [
            e for e in expenditures
            if e.beneficiary_territory_id == t.id and not getattr(e, "is_synthetic", False)
        ]
        amount = sum((amount_for_public_kpi(e) for e in rows), start=Decimal("0"))
        out.append(
            {
                "slug": slug,
                "name": name,
                "level": coverage_level(len(rows)),
                "expenditures": len(rows),
                "amount_direct_verifiable": float(amount),
            }
        )
    return out
