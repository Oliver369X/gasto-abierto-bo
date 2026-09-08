#!/usr/bin/env python3
"""Load deep multi-source corpus + run cross-source reconciliation.

Offline-safe. Uses skip_storage + skip_alerts during ingest to avoid hangs
in constrained Docker. Progress logs every step.

  python -m scripts.cli gasto seed --profile deep
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
from worker.gasto.seeds._helpers import (
    seed_log,
    seed_skip_alerts_during_ingest,
    seed_skip_storage,
)
from worker.pipeline import run_ingest
from worker.reconcile import reconcile_all

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "[REDACTED]ql+psycopg://gasto:gasto_dev_change_me@[REDACTED]:5434/gasto_abierto",
)
FIX = ROOT / "tests" / "fixtures"


def _ensure_deep_fixtures() -> None:
    deep_agetic = FIX / "agetic" / "deep" / "contracts_2019_2025_deep.csv"
    if deep_agetic.exists():
        return
    seed_log("deep", "generating deep fixtures (first run)")
    import subprocess

    script = ROOT / "scripts" / "_legacy" / "generate_deep_corpus.py"
    subprocess.run([sys.executable, str(script)], check=True, cwd=str(ROOT))


def _ingest_step(
    session,
    source_id: str,
    fixture_path: str,
    *,
    skip_storage: bool,
    skip_alerts: bool,
) -> dict:
    seed_log("deep", f"ingest {source_id} from {Path(fixture_path).name}")
    result = run_ingest(
        session,
        source_id,
        fixture_path=fixture_path,
        live=False,
        skip_storage=skip_storage,
        skip_alerts=skip_alerts,
    )
    session.commit()
    seed_log("deep", f"ingest {source_id} records={result.get('records', 0)}")
    return result


def main() -> None:
    _ensure_deep_fixtures()
    skip_storage = seed_skip_storage()
    skip_alerts = seed_skip_alerts_during_ingest()

    Session = sessionmaker(bind=make_engine(DATABASE_URL), autoflush=False, autocommit=False)
    session = Session()
    try:
        results: dict = {}
        results["agetic"] = _ingest_step(
            session,
            "agetic",
            str(FIX / "agetic" / "deep"),
            skip_storage=skip_storage,
            skip_alerts=skip_alerts,
        )
        results["sicoes"] = _ingest_step(
            session,
            "sicoes",
            str(FIX / "sicoes" / "deep"),
            skip_storage=skip_storage,
            skip_alerts=skip_alerts,
        )
        results["presupuesto_abierto"] = _ingest_step(
            session,
            "presupuesto_abierto",
            str(FIX / "presupuesto_abierto" / "deep"),
            skip_storage=skip_storage,
            skip_alerts=skip_alerts,
        )
        results["cge"] = _ingest_step(
            session,
            "cge",
            str(FIX / "cge" / "deep"),
            skip_storage=skip_storage,
            skip_alerts=skip_alerts,
        )

        seed_log("deep", "reconcile cross-source")
        recon = reconcile_all(session)
        session.commit()
        results["reconcile"] = recon
        seed_log("deep", f"reconcile cuce={recon.get('cuce_discrepancies')} budget={recon.get('budget_vs_contracts')}")

        seed_log("deep", "refreshing alerts")
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

        print(results, flush=True)
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
        seed_log("deep", "done")
        print("Seed deep OK", flush=True)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
