#!/usr/bin/env python3
"""Seed ALL gestiones (multi-year SICOES history) into Postgres.

  python scripts/download_sicoes_all_years.py
  python scripts/build_sicoes_all_years.py
  python scripts/seed_all_years.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(ROOT / "services"))

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from schema.db import make_engine
from schema.models import Contract, Discrepancy, Entity
from worker.alerts import run_alert_rules
from worker.pipeline import run_ingest
from worker.reconcile import reconcile_all

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://gasto:gasto_dev_change_me@localhost:5434/gasto_abierto",
)
BY_YEAR = ROOT / "tests" / "fixtures" / "real" / "corpus" / "by_year"
CORPUS = ROOT / "tests" / "fixtures" / "real" / "corpus"


def main() -> None:
    import runpy

    if not BY_YEAR.exists() or not list(BY_YEAR.glob("sicoes_*.csv")):
        hist = ROOT / "tests" / "fixtures" / "real" / "sicoes_history" / "months"
        if not hist.exists() or len(list(hist.glob("*.csv"))) < 50:
            runpy.run_path(
                str(ROOT / "scripts" / "download_sicoes_all_years.py"), run_name="__main__"
            )
        runpy.run_path(str(ROOT / "scripts" / "build_sicoes_all_years.py"), run_name="__main__")

    Session = sessionmaker(bind=make_engine(DATABASE_URL), autoflush=False, autocommit=False)
    session = Session()
    year_files = sorted(BY_YEAR.glob("sicoes_*.csv"))
    print(f"ingesting {len(year_files)} year files…")
    results = []
    try:
        for path in year_files:
            print("→", path.name)
            # Primary mirror as sicoes
            r = run_ingest(
                session,
                "sicoes",
                fixture_path=str(path),
                live=False,
                skip_alerts=True,
                skip_storage=True,
            )
            session.commit()
            results.append({"file": path.name, "source": "sicoes", **r})
            # Contrast copy as agetic for 2019-2020 only (overlap with official OCDS)
            year = int(path.stem.split("_")[1])
            if year in (2019, 2020) and (CORPUS / "agetic_contracts.csv").exists():
                # already have official agetic; skip duplicate year dump as agetic
                pass

        # Official OCDS contrast (montos reales) if present
        for name, source in (
            ("agetic_contracts.csv", "agetic"),
            ("sicoes_contracts.csv", "sicoes"),
            ("ocp_contracts.csv", "agetic"),
        ):
            p = CORPUS / name
            if p.exists() and p.stat().st_size > 50:
                print("→ official", name)
                r = run_ingest(
                    session,
                    source,
                    fixture_path=str(p),
                    live=False,
                    skip_alerts=True,
                    skip_storage=True,
                )
                session.commit()
                results.append({"file": name, **r})

        budget = CORPUS / "projects_as_budget.json"
        if budget.exists():
            print("→ projects budget")
            r = run_ingest(
                session,
                "presupuesto_abierto",
                fixture_path=str(budget),
                live=False,
                skip_alerts=True,
                skip_storage=True,
            )
            session.commit()
            results.append({"file": "projects_as_budget.json", **r})

        print("reconcile…")
        if os.getenv("SEED_SKIP_RECONCILE", "0") == "1":
            recon = {"skipped": True}
        else:
            # Only reconcile recent years to keep memory bounded
            recon = reconcile_all(session)
        session.commit()
        print("alerts (final)…")
        if os.getenv("SEED_SKIP_ALERTS", "1") == "1":
            n_alerts = 0
        else:
            n_alerts = len(run_alert_rules(session))
        session.commit()

        years = session.execute(
            select(func.extract("year", Contract.contract_date), func.count())
            .where(Contract.is_current.is_(True), Contract.contract_date.is_not(None))
            .group_by(func.extract("year", Contract.contract_date))
            .order_by(func.extract("year", Contract.contract_date))
        ).all()
        totals = {
            "entities": session.scalar(select(func.count()).select_from(Entity)) or 0,
            "contracts": session.scalar(
                select(func.count()).select_from(Contract).where(Contract.is_current.is_(True))
            )
            or 0,
            "discrepancies": session.scalar(select(func.count()).select_from(Discrepancy)) or 0,
            "alerts": n_alerts,
            "years": {int(y): int(c) for y, c in years if y is not None},
            "reconcile": recon,
            "files": len(results),
        }
        print(totals)
        if totals["contracts"] < 50_000:
            raise SystemExit(f"expected >=50k contracts across gestiones, got {totals['contracts']}")
        if len(totals["years"]) < 8:
            raise SystemExit(f"expected many years, got {totals['years']}")
        print("Seed ALL YEARS OK")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
