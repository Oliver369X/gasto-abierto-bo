#!/usr/bin/env python3
"""Ingest SICOES fixture with overlapping CUCEs (different amounts) to demo discrepancies."""
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
from schema.models import Discrepancy
from worker.adapters.agetic import AgeticAdapter
from worker.adapters.base import Cursor
from worker.gasto.seeds._helpers import seed_log, seed_skip_storage
from worker.persist import finish_run, persist_staging, start_run
from worker.reconcile import reconcile_all

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://gasto:gasto_dev_change_me@localhost:5434/gasto_abierto",
)
FIXTURE = ROOT / "tests" / "fixtures" / "sicoes" / "contracts_overlap_agetic.csv"


def main() -> None:
    Session = sessionmaker(bind=make_engine(DATABASE_URL), autoflush=False, autocommit=False)
    session = Session()
    skip_storage = seed_skip_storage()
    try:
        adapter = AgeticAdapter()
        items = adapter.discover(Cursor(payload={"fixture_path": str(FIXTURE)}))
        run = start_run(session, "sicoes", meta={"kind": "cross_source_overlap"})
        all_recs = []
        for item in items:
            raw = adapter.fetch(item)
            for rec in adapter.parse(raw):
                rec.data["source_id"] = "sicoes"
                all_recs.append(rec)
        n = persist_staging(session, all_recs, source_id="sicoes", run=run)
        finish_run(session, run, status="ok", records_in=len(items), records_out=n)
        session.commit()
        seed_log("cross", f"overlap records={n} run_id={run.id}")

        seed_log("cross", "reconcile cross-source")
        recon = reconcile_all(session)
        session.commit()
        n_disc = session.scalar(select(func.count()).select_from(Discrepancy)) or 0
        seed_log("cross", f"reconcile={recon} discrepancies={n_disc}")
        if skip_storage:
            seed_log("cross", "MINIO skipped (SEED_SKIP_STORAGE=1)")
        if n_disc < 1:
            raise SystemExit(
                "cross: no discrepancies — run demo/history first so agetic CUCEs exist, then cross"
            )
        print(f"cross_source_overlap records={n} discrepancies={n_disc}", flush=True)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
