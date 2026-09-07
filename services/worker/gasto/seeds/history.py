#!/usr/bin/env python3
"""Load multi-year historical fixtures (2019–2025) into the DB.

Safe offline path — no live network. Run inside Docker:

  docker compose run --rm api python scripts/seed_history.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(ROOT / "services"))

from sqlalchemy.orm import sessionmaker

from schema.db import make_engine
from worker.adapters.base import StagingRecord
from worker.adapters.presupuesto_abierto import PresupuestoAbiertoAdapter
from worker.pipeline import run_ingest
from worker.persist import finish_run, persist_staging, start_run

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://gasto:gasto_dev_change_me@localhost:5434/gasto_abierto",
)
FIXTURES = ROOT / "tests" / "fixtures"


def load_presupuesto_history(session) -> int:
    path = FIXTURES / "presupuesto_abierto" / "history_2019_2025.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    adapter = PresupuestoAbiertoAdapter()
    # Reuse parser by reshaping to entidades format per year batch
    records: list[StagingRecord] = []
    for row in data["series"]:
        payload = {
            "entidades": [
                {
                    "entidad": row["entidad"],
                    "nivel": row["nivel"],
                    "gestion": row["gestion"],
                    "presupuesto_inicial": row["presupuesto_inicial"],
                    "presupuesto_vigente": row["presupuesto_vigente"],
                    "ejecucion": row["ejecucion"],
                }
            ]
        }
        records.extend(adapter.parse(json.dumps(payload).encode("utf-8")))
    run = start_run(session, "presupuesto_abierto", meta={"kind": "history_2019_2025"})
    n = persist_staging(session, records, source_id="presupuesto_abierto", run=run)
    finish_run(session, run, status="ok", records_in=len(records), records_out=n)
    return n


def main() -> None:
    Session = sessionmaker(bind=make_engine(DATABASE_URL), autoflush=False, autocommit=False)
    session = Session()
    try:
        # Historical contracts CSV via full pipeline (MinIO + documents)
        hist_csv = FIXTURES / "agetic" / "contracts_history_2019_2025.csv"
        result = run_ingest(
            session,
            "agetic",
            fixture_path=str(hist_csv),
            live=False,
        )
        session.commit()
        print("contracts_history:", result)

        n = load_presupuesto_history(session)
        session.commit()
        print(f"presupuesto_history_rows: {n}")

        from worker.alerts import run_alert_rules

        alerts = run_alert_rules(session)
        session.commit()
        print(f"alerts_refreshed: {len(alerts)}")
        print("Seed history OK")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
