"""B2 — prioritized SICOES enrich queue with rate limit and dry-run."""
from __future__ import annotations

import os
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from schema.db import make_engine
from schema.models import Contract
from worker.enrich_sicoes import enrich_sicoes_cuce, prioritize_cuces

RATE_SECONDS = float(os.getenv("SICOES_ENRICH_RPS", "1.0"))
PROXY_URL = os.getenv("PROXY_URL", "").strip()
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://gasto:gasto_dev_change_me@localhost:5434/gasto_abierto",
)


def enqueue_prioritized(
    session: Session, *, year_from: int, limit: int
) -> list[str]:
    """Prioritize CUCEs; filter contract_date year >= year_from when possible."""
    candidates = prioritize_cuces(session, limit=max(limit * 5, limit))
    if not candidates:
        return []
    rows = {
        r.cuce: r
        for r in session.scalars(
            select(Contract).where(
                Contract.is_current.is_(True),
                Contract.cuce.in_(candidates),
            )
        ).all()
        if r.cuce
    }
    out: list[str] = []
    for cuce in candidates:
        c = rows.get(cuce)
        if not c:
            continue
        if c.contract_date is not None and c.contract_date.year < year_from:
            continue
        out.append(cuce)
        if len(out) >= limit:
            break
    # If year filter emptied the list (all null dates), fall back to prioritize order
    if not out and candidates:
        return candidates[:limit]
    return out


def run_batch(
    session: Session, cuces: list[str], *, dry_run: bool = False
) -> dict[str, Any]:
    """Enrich each CUCE; rate-limited via SICOES_ENRICH_RPS."""
    results: list[dict[str, Any]] = []
    rps = max(RATE_SECONDS, 0.01)
    sleep_s = 1.0 / rps
    for i, cuce in enumerate(cuces):
        if dry_run:
            results.append({"ok": True, "cuce": cuce, "dry_run": True})
            continue
        if i > 0:
            time.sleep(sleep_s)
        results.append(enrich_sicoes_cuce(session, cuce))
    return {
        "ok": True,
        "count": len(cuces),
        "dry_run": dry_run,
        "results": results,
        "cuces": cuces,
    }


def run_cli(limit: int, year_from: int, dry_run: bool) -> dict[str, Any]:
    """Open DB from DATABASE_URL; block live enrich without PROXY_URL."""
    engine = make_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with SessionLocal() as session:
        cuces = enqueue_prioritized(session, year_from=year_from, limit=limit)
        if not dry_run and not PROXY_URL:
            return {
                "ok": True,
                "blocked": "no_proxy",
                "enrich_skipped_no_proxy": True,
                "cuces": cuces,
            }
        out = run_batch(session, cuces, dry_run=dry_run)
        if not dry_run:
            session.commit()
        return out
