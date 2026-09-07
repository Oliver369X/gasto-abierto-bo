from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation


_CLEAN = re.compile(r"[^\d,.\-]")


def parse_money(value: str | int | float | Decimal | None) -> Decimal | None:
    """Parse Bolivian/EU/US money strings into Decimal.

    Examples: '1.200.000,50', '1,200,000.50', 'Bs 50000', '50.000'
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))

    s = str(value).strip()
    if not s:
        return None
    s = _CLEAN.sub("", s)
    if not s or s in {"-", ".", ","}:
        return None

    # Both separators: last one is decimal
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            # 1.200.000,50
            s = s.replace(".", "").replace(",", ".")
        else:
            # 1,200,000.50
            s = s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        if len(parts[-1]) <= 2 and len(parts) == 2:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "." in s:
        parts = s.split(".")
        # Bolivian thousands: 50.000 or 1.200.000 (groups of 3)
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]) and len(parts[-1]) == 3:
            s = s.replace(".", "")
        elif s.count(".") > 1:
            s = s.replace(".", "")

    try:
        return Decimal(s)
    except InvalidOperation:
        return None
