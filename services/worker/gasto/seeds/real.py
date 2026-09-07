#!/usr/bin/env python3
"""Ingest REAL open-data corpus + deep historical contrast into Postgres.

  python -m scripts.cli gasto fetch-open-data
  python scripts/build_real_corpus.py
  python -m scripts.cli gasto seed --profile real
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
from schema.models import AuditReport, BudgetLine, Contract, Discrepancy, Entity
from worker.alerts import run_alert_rules
from worker.pipeline import run_ingest
from worker.reconcile import reconcile_all

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://gasto:gasto_dev_change_me@localhost:5434/gasto_abierto",
)
REAL = ROOT / "tests" / "fixtures" / "real"
CORPUS = REAL / "corpus"


def main() -> None:
    if not (CORPUS / "agetic_contracts.csv").exists():
        import runpy

        if not (REAL / "agetic" / "sicoes_ocp_2019.csv").exists():
            from common.fetch_open_data import fetch_packages

            fetch_packages(REAL, force=False)
        runpy.run_path(str(ROOT / "scripts" / "_legacy" / "build_real_corpus.py"), run_name="__main__")

    deep_a = ROOT / "tests" / "fixtures" / "agetic" / "deep"
    if not (deep_a / "contracts_2019_2025_deep.csv").exists():
        import runpy

        runpy.run_path(str(ROOT / "scripts" / "_legacy" / "generate_deep_corpus.py"), run_name="__main__")

    Session = sessionmaker(bind=make_engine(DATABASE_URL), autoflush=False, autocommit=False)
    session = Session()
    results: dict = {}
    try:
        results["real_agetic"] = run_ingest(
            session, "agetic", fixture_path=str(CORPUS / "agetic_contracts.csv"), live=False
        )
        session.commit()
        results["real_sicoes"] = run_ingest(
            session, "sicoes", fixture_path=str(CORPUS / "sicoes_contracts.csv"), live=False
        )
        session.commit()
        results["real_ocp"] = run_ingest(
            session, "agetic", fixture_path=str(CORPUS / "ocp_contracts.csv"), live=False
        )
        session.commit()
        results["real_projects_budget"] = run_ingest(
            session,
            "presupuesto_abierto",
            fixture_path=str(CORPUS / "projects_as_budget.json"),
            live=False,
        )
        session.commit()

        # Volume + multi-year contrast
        results["deep_agetic"] = run_ingest(
            session, "agetic", fixture_path=str(deep_a), live=False
        )
        session.commit()
        results["deep_sicoes"] = run_ingest(
            session,
            "sicoes",
            fixture_path=str(ROOT / "tests" / "fixtures" / "sicoes" / "deep"),
            live=False,
        )
        session.commit()
        results["deep_presupuesto"] = run_ingest(
            session,
            "presupuesto_abierto",
            fixture_path=str(ROOT / "tests" / "fixtures" / "presupuesto_abierto" / "deep"),
            live=False,
        )
        session.commit()
        results["deep_cge"] = run_ingest(
            session,
            "cge",
            fixture_path=str(ROOT / "tests" / "fixtures" / "cge" / "deep"),
            live=False,
        )
        session.commit()

        hist = ROOT / "tests" / "fixtures" / "agetic" / "contracts_history_2019_2025.csv"
        if hist.exists():
            results["history"] = run_ingest(session, "agetic", fixture_path=str(hist), live=False)
            session.commit()
        overlap = ROOT / "tests" / "fixtures" / "sicoes" / "contracts_overlap_agetic.csv"
        if overlap.exists():
            results["overlap"] = run_ingest(session, "sicoes", fixture_path=str(overlap), live=False)
            session.commit()

        results["reconcile"] = reconcile_all(session)
        session.commit()
        results["alerts"] = len(run_alert_rules(session))
        session.commit()

        totals = {
            "entities": session.scalar(select(func.count()).select_from(Entity)) or 0,
            "contracts": session.scalar(
                select(func.count()).select_from(Contract).where(Contract.is_current.is_(True))
            )
            or 0,
            "budgets": session.scalar(
                select(func.count()).select_from(BudgetLine).where(BudgetLine.is_current.is_(True))
            )
            or 0,
            "audits": session.scalar(select(func.count()).select_from(AuditReport)) or 0,
            "discrepancies": session.scalar(select(func.count()).select_from(Discrepancy)) or 0,
        }
        results["totals"] = totals
        print(results)
        if totals["contracts"] < 150:
            raise SystemExit("seed_real: expected large contract corpus")
        print("Seed REAL OK")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
