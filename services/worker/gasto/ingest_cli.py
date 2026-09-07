#!/usr/bin/env python3
"""Enqueue or run ingestion jobs.

Examples:
  python scripts/ingest.py --source sicoes --sync
  python scripts/ingest.py --all --sync
  python scripts/ingest.py --source agetic --enqueue
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(ROOT / "services"))

from sqlalchemy.orm import sessionmaker

from schema.db import make_engine
from worker.pipeline import run_ingest

SOURCES = [
    "agetic",
    "sicoes",
    "presupuesto_abierto",
    "cge",
    "gad_scz",
    "gam_scz",
]
FIXTURES = {
    "agetic": "sample_contracts.csv",
    "sicoes": "procesos_sample.html",
    "presupuesto_abierto": "entidades.json",
    "cge": "informes_sample.html",
    "gad_scz": "portal_sample.html",
    "gam_scz": "rendicion_text.txt",
}


def sync_ingest(source_id: str, live: bool) -> dict:
    url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://gasto:gasto_dev_change_me@localhost:5434/gasto_abierto",
    )
    Session = sessionmaker(bind=make_engine(url), autoflush=False, autocommit=False)
    session = Session()
    fixture = None
    if not live:
        path = ROOT / "tests" / "fixtures" / source_id / FIXTURES[source_id]
        fixture = str(path)
    try:
        result = run_ingest(session, source_id, fixture_path=fixture, live=live)
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def enqueue(source_id: str | None, all_sources: bool) -> None:
    from arq import create_pool
    from arq.connections import RedisSettings

    redis = await create_pool(RedisSettings.from_dsn(os.getenv("REDIS_URL", "redis://localhost:6380/0")))
    if all_sources:
        job = await redis.enqueue_job("ingest_all_mvp")
        print(f"enqueued ingest_all_mvp job_id={job.job_id}")
    else:
        job = await redis.enqueue_job("ingest_source", source_id)
        print(f"enqueued ingest_source({source_id}) job_id={job.job_id}")
    await redis.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Gasto Abierto — ingest CLI")
    parser.add_argument("--source", choices=SOURCES)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--sync", action="store_true", help="Run in-process (no Redis)")
    parser.add_argument("--enqueue", action="store_true", help="Enqueue ARQ job")
    parser.add_argument("--live", action="store_true", help="Hit live portals")
    args = parser.parse_args()

    if not args.source and not args.all:
        parser.error("Provide --source or --all")

    if args.enqueue:
        asyncio.run(enqueue(args.source, args.all))
        return

    if not args.sync:
        parser.error("Use --sync or --enqueue")

    targets = SOURCES if args.all else [args.source]
    for sid in targets:
        result = sync_ingest(sid, live=args.live or os.getenv("LIVE_SCRAPE") == "1")
        print(result)


if __name__ == "__main__":
    main()
