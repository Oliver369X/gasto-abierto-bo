#!/usr/bin/env python3
"""Backfill category on existing contracts / budget lines."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(ROOT / "services"))

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from common.categorize import categorize
from schema.db import make_engine
from schema.models import BudgetLine, Contract

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://gasto:gasto_dev_change_me@localhost:5434/gasto_abierto",
)


def main() -> None:
    Session = sessionmaker(bind=make_engine(DATABASE_URL), autoflush=False, autocommit=False)
    session = Session()
    try:
        n_c = 0
        for row in session.scalars(select(Contract).where(Contract.is_current.is_(True))).all():
            cat = categorize(
                object_description=row.object_description,
                modality=row.modality,
            )
            if row.category != cat:
                row.category = cat
                n_c += 1
        n_b = 0
        for row in session.scalars(select(BudgetLine).where(BudgetLine.is_current.is_(True))).all():
            cat = categorize(
                program_project=row.program_project,
                budget_item=row.budget_item,
            )
            if row.category != cat:
                row.category = cat
                n_b += 1
        session.commit()
        print(f"updated contracts={n_c} budgets={n_b}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
