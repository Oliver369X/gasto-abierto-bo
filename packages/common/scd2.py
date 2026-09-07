from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session


def close_current(
    session: Session,
    model: type,
    match_filters: dict[str, Any],
    *,
    closed_at: datetime | None = None,
) -> int:
    """Mark current SCD2 rows as closed. Returns number of rows closed."""
    closed_at = closed_at or datetime.now(timezone.utc)
    stmt = select(model).filter_by(is_current=True, **match_filters)
    rows = session.scalars(stmt).all()
    for row in rows:
        row.is_current = False
        row.valid_to = closed_at
    return len(rows)


def upsert_versioned(
    session: Session,
    model: type,
    match_filters: dict[str, Any],
    values: dict[str, Any],
    *,
    equal_fn: Callable[[Any, dict[str, Any]], bool] | None = None,
) -> Any:
    """Insert a new current version if values changed; else return existing."""
    now = datetime.now(timezone.utc)
    stmt = select(model).filter_by(is_current=True, **match_filters)
    current = session.scalars(stmt).first()
    if current is not None:
        if equal_fn is not None and equal_fn(current, values):
            return current
        # shallow equality on provided keys
        if equal_fn is None and all(getattr(current, k, None) == v for k, v in values.items()):
            return current
        current.is_current = False
        current.valid_to = now

    row = model(
        **match_filters,
        **values,
        valid_from=now,
        valid_to=None,
        is_current=True,
    )
    session.add(row)
    return row
