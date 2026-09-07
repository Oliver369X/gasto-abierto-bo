"""Helpers for honest fire ledger KPIs (F1)."""
from __future__ import annotations

from decimal import Decimal
from typing import Any


def _attr(row: Any) -> str:
    a = getattr(row, "attribution", None)
    return a.value if hasattr(a, "value") else str(a or "")


def _dec(v: Any) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def is_public_verifiable(row: Any) -> bool:
    """Only clearly defined, non-synthetic, quality-A directo amounts."""
    if getattr(row, "is_synthetic", False):
        return False
    ev = getattr(row, "evidence", None) or {}
    if isinstance(ev, dict) and ev.get("is_synthetic"):
        return False
    bucket = getattr(row, "ledger_bucket", None)
    if bucket == "sintetico":
        return False
    if (getattr(row, "quality_grade", "") or "").upper() != "A":
        return False
    if _attr(row) != "directo":
        return False
    return _dec(getattr(row, "amount_attributed", None)) > 0


def amount_for_public_kpi(row: Any) -> Decimal:
    if not is_public_verifiable(row):
        return Decimal("0")
    return _dec(getattr(row, "amount_attributed", None))


def amount_by_bucket(row: Any) -> tuple[str, Decimal]:
    bucket = getattr(row, "ledger_bucket", None) or "probable"
    if getattr(row, "is_synthetic", False) or bucket == "sintetico":
        return "sintetico", Decimal("0")
    amt = _dec(getattr(row, "amount_attributed_base", None) or getattr(row, "amount_attributed", None))
    return str(bucket), amt
