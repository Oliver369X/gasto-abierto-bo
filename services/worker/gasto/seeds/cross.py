#!/usr/bin/env python3
"""Ingest SICOES fixture with overlapping CUCEs (different amounts) to demo discrepancies."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(ROOT / "services"))

from sqlalchemy.orm import sessionmaker

from schema.db import make_engine
from worker.pipeline import run_ingest

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://gasto:gasto_dev_change_me@localhost:5434/gasto_abierto",
)
FIXTURE = ROOT / "tests" / "fixtures" / "sicoes" / "contracts_overlap_agetic.csv"


def main() -> None:
    # Reuse agetic CSV parser via temporary source: register path as agetic-compatible
    # by pointing sicoes fixture through agetic adapter format (CSV).
    Session = sessionmaker(bind=make_engine(DATABASE_URL), autoflush=False, autocommit=False)
    session = Session()
    try:
        # Persist as source_id sicoes using agetic CSV parser path:
        # Use a thin wrapper: run_ingest agetic-style but we need sicoes source_id.
        from worker.adapters.agetic import AgeticAdapter
        from worker.adapters.base import Cursor
        from worker.persist import finish_run, persist_staging, start_run
        from common.storage import get_store
        from schema.models import Document

        adapter = AgeticAdapter()
        items = adapter.discover(Cursor(payload={"fixture_path": str(FIXTURE)}))
        run = start_run(session, "sicoes", meta={"kind": "cross_source_overlap"})
        store = get_store()
        all_recs = []
        for idx, item in enumerate(items):
            raw = adapter.fetch(item)
            key = store.put_bytes(
                source_id="sicoes",
                key_suffix=f"run-{run.id}/item-{idx}",
                data=raw,
                content_type="text/csv",
            )
            sha = store.sha256(raw)
            session.add(
                Document(
                    url=item.uri,
                    sha256=sha,
                    mime="text/csv",
                    minio_key=key,
                    source_id="sicoes",
                    ingestion_run_id=run.id,
                )
            )
            for rec in adapter.parse(raw):
                rec.data["source_id"] = "sicoes"
                if key:
                    rec.data["minio_key"] = key
                    rec.data["raw_sha256"] = sha
                all_recs.append(rec)
        n = persist_staging(session, all_recs, source_id="sicoes", run=run)
        finish_run(session, run, status="ok", records_in=len(items), records_out=n)
        session.commit()
        print(f"cross_source_overlap records={n} run_id={run.id}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
