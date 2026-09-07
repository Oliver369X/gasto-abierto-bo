"""Common FireExpenditure / FireLink repository helpers."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from schema.models import FireExpenditure, FireLink


def get_exp_by_cuce(session: Session, cuce: str) -> FireExpenditure | None:
    return session.scalars(select(FireExpenditure).where(FireExpenditure.cuce == cuce)).first()


def list_aero(session: Session, *, year: int | None = None) -> list[FireExpenditure]:
    stmt = select(FireExpenditure).where(
        FireExpenditure.code.like("%AERO%"),
        FireExpenditure.is_synthetic.is_(False),
    )
    if year is not None:
        stmt = stmt.where(FireExpenditure.year == year)
    return list(session.scalars(stmt).all())


def purge_links_by_resolver(session: Session, resolver: str) -> int:
    rows = list(session.scalars(select(FireLink)).all())
    n = 0
    for link in rows:
        ev = link.evidence or {}
        if ev.get("resolver") == resolver:
            session.delete(link)
            n += 1
    session.flush()
    return n
