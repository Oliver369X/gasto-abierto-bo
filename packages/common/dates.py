from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from dateutil import parser as date_parser


def parse_date_flexible(value: str | date | datetime | None) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s:
        return None
    # DD/MM/YYYY common in BO
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    try:
        return date_parser.parse(s, dayfirst=True).date()
    except (ValueError, OverflowError, TypeError):
        return None
