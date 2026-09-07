#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "packages"), str(ROOT / "services")]

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from schema.db import make_engine
from schema.models import Discrepancy, FireExpenditure, FireSeason, OperationalOutput

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://gasto:gasto_dev_change_me@localhost:5434/gasto_abierto",
)


def main() -> None:
    session = sessionmaker(bind=make_engine(DATABASE_URL))()
    years = session.scalars(select(FireSeason.year).order_by(FireSeason.year)).all()
    print("seasons", len(years), years[:5], "...", years[-5:])

    ha = session.execute(
        select(OperationalOutput.year, OperationalOutput.value_numeric)
        .where(OperationalOutput.metric_key == "hectareas_quemadas_dgf_simb")
        .order_by(OperationalOutput.year)
    ).all()
    print("ha_rows", len(ha))
    if ha:
        peak = max(ha, key=lambda x: float(x[1]))
        print("first", ha[0], "last", ha[-1], "peak", peak)

    for y in (2022, 2023, 2024, 2025, 2026):
        n = session.scalar(
            select(func.count()).select_from(OperationalOutput).where(OperationalOutput.year == y)
        )
        e = session.scalar(
            select(func.count()).select_from(FireExpenditure).where(FireExpenditure.year == y)
        )
        print(f"year {y}: ops={n} exp={e}")

    real = session.scalars(
        select(FireExpenditure)
        .where(FireExpenditure.code.like("FIRE-BO-%-REAL-%"))
        .order_by(FireExpenditure.code)
    ).all()
    print("REAL expenditures", len(real))
    for r in real:
        attr = getattr(r.attribution, "value", r.attribution)
        print(r.year, r.code, attr, r.amount_attributed, r.quality_grade)

    disc = session.scalars(select(Discrepancy).where(Discrepancy.concept.like("fire:%"))).all()
    print("fire discrepancies", len(disc))
    for d in disc:
        print(d.concept, d.amount_a, "vs", d.amount_b)
    session.close()


if __name__ == "__main__":
    main()
