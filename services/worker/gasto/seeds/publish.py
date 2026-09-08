#!/usr/bin/env python3
"""Publishable offline seed: deep corpus + cross-source reconcile + harden (G10).

Use after `docker compose up` when MinIO is optional/disabled:

  docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile publish

Then verify:

  bash scripts/verify_mvp.sh  # incluye S16 product-gate
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
from schema.models import AuditFinding, Claim, ClaimEvidence, Discrepancy, PublicEntityMaster
from worker.gasto.seeds._helpers import seed_log
from worker.gasto.seeds import deep




def main() -> None:
    seed_log("publish", "running deep corpus + reconcile")
    deep.main()

    seed_log("publish", "harden masters / claims / findings")
    from worker.gasto.harden_impl import main as harden_main

    harden_main()

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise SystemExit("publish: DATABASE_URL required")
    Session = sessionmaker(bind=make_engine(db_url), autoflush=False, autocommit=False)
    session = Session()
    try:
        em = session.scalar(select(func.count()).select_from(PublicEntityMaster)) or 0
        claims = session.scalar(select(func.count()).select_from(Claim)) or 0
        evidence = session.scalar(select(func.count()).select_from(ClaimEvidence)) or 0
        findings = session.scalar(select(func.count()).select_from(AuditFinding)) or 0
        discs = session.scalar(select(func.count()).select_from(Discrepancy)) or 0
        seed_log(
            "publish",
            f"entity_masters={em} claims={claims} evidence={evidence} findings={findings} discrepancies={discs}",
        )
        if discs < 1:
            raise SystemExit("publish: expected discrepancies after deep reconcile")
        if claims < 50:
            raise SystemExit("publish: expected >=50 claims after harden")
        if evidence < claims * 0.8:
            raise SystemExit("publish: expected >=80% claims with evidence after harden")
        if findings < 20:
            raise SystemExit("publish: expected >=20 audit findings after harden")
    finally:
        session.close()

    seed_log("publish", "fire demo corpus (AURA incendios)")
    from worker.gasto.seeds import fire_demo

    try:
        fire_demo.main(force=False)
    except SystemExit as exc:
        raise SystemExit(f"publish: fire_demo failed ({exc})") from exc

    # Post-check: ledger should have expenditures for demo year.
    session = Session()
    try:
        from schema.models import FireExpenditure

        fire_rows = session.scalar(select(func.count()).select_from(FireExpenditure)) or 0
        if fire_rows < 1:
            raise SystemExit("publish: fire_demo produced zero fire_expenditure rows")
        seed_log("publish", f"fire_expenditures={fire_rows}")
    finally:
        session.close()

    print("Seed publish OK", flush=True)


if __name__ == "__main__":
    main()
