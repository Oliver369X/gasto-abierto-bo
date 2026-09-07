from __future__ import annotations

import re


_NON_ALNUM = re.compile(r"[^A-Z0-9]+")


def normalize_cuce(value: str | None) -> str | None:
    """Canonical CUCE / OCID key for cross-source joins.

    Strips whitespace, uppercases, collapses separators so
    ``ocds-2019-001``, ``OCDS 2019/001`` and ``OCDS-2019-001`` match.
    """
    if value is None:
        return None
    raw = str(value).strip().upper()
    if not raw:
        return None
    collapsed = _NON_ALNUM.sub("-", raw).strip("-")
    return collapsed or None
