#!/usr/bin/env python3
"""Load deep multi-source corpus + run cross-source reconciliation.

Offline-safe. Intended for Docker:

  python scripts/generate_deep_corpus.py
  python scripts/seed_deep.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(ROOT / "services"))

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from schema.db import make_engine
from schema.models import Contract, Discrepancy
from worker.alerts import run_alert_rules
from worker.pipeline import run_ingest
from worker.reconcile import reconcile_all

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://gasto:gasto_dev_change_me@localhost:5434/gasto_abierto",
)
FIX = ROOT / "tests" / "fixtures"


def main() -> None:
    deep_agetic = FIX / "agetic" / "deep" / "contracts_2019_2025_deep.csv"
    if not deep_agetic.exists():
        import runpy

        runpy.run_path(str(ROOT / "scripts" / "_legacy" / "generate_deep_corpus.py"), run_name="__main__")

    Session = sessionmaker(bind=make_engine(DATABASE_URL), autoflush=False, autocommit=False)
    session = Session()
    try:
        results: dict = {}
        results["agetic"] = run_ingest(
            session,
            "agetic",
            fixture_path=str(FIX / "agetic" / "deep"),
            live=False,
        )
        session.commit()

        results["sicoes"] = run_ingest(
            session,
            "sicoes",
            fixture_path=str(FIX / "sicoes" / "deep"),
            live=False,
        )
        session.commit()

        results["presupuesto_abierto"] = run_ingest(
            session,
            "presupuesto_abierto",
            fixture_path=str(FIX / "presupuesto_abierto" / "deep"),
            live=False,
        )
        session.commit()

        results["cge"] = run_ingest(
            session,
            "cge",
            fixture_path=str(FIX / "cge" / "deep"),
            live=False,
        )
        session.commit()

        recon = reconcile_all(session)
        session.commit()
        results["reconcile"] = recon

        alerts = run_alert_rules(session)
        session.commit()
        results["alerts"] = len(alerts)

        n_contracts = (
            session.scalar(
                select(func.count()).select_from(Contract).where(Contract.is_current.is_(True))
            )
            or 0
        )
        n_disc = session.scalar(select(func.count()).select_from(Discrepancy)) or 0
        results["totals"] = {"contracts": n_contracts, "discrepancies": n_disc}

        print(results)
        agetic_n = int(
            results["agetic"].get("records")
            or results["agetic"].get("records_out")
            or 0
        )
        if agetic_n < 50:
            raise SystemExit("seed_deep: too few agetic records")
        if n_disc < 5:
            raise SystemExit("seed_deep: expected CUCE cross-source discrepancies in DB")
        if n_contracts < 80:
            raise SystemExit("seed_deep: expected deep contract corpus")
        print("Seed deep OK")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
