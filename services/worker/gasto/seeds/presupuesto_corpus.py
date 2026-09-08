#!/usr/bin/env python3
"""Seed Presupuesto Abierto from bundled offline corpus when download URLs are empty.

Safe for CI/staging without network. Uses manifest at
tests/fixtures/presupuesto_abierto/offline_corpus_manifest.json.

  docker compose run --rm --entrypoint python api \\
    -m scripts.cli gasto seed --profile presupuesto_corpus
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(ROOT / "services"))

from common.fetch_presupuesto_abierto import (
    list_offline_corpus_paths,
    load_offline_manifest,
)
from sqlalchemy.orm import sessionmaker

from schema.db import make_engine
from worker.gasto.seeds._helpers import (
    seed_log,
    seed_skip_alerts_during_ingest,
    seed_skip_storage,
)
from worker.pipeline import run_ingest

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "[REDACTED]ql+psycopg://gasto:gasto_dev_change_me@[REDACTED]:5434/gasto_abierto",  # pragma: allowlist secret
)
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "presupuesto_abierto"


def _urls_configured() -> bool:
    for key in ("PRESUPUESTO_ABIERTO_DOWNLOAD_URLS", "PRESUPUESTO_ABIERTO_URLS"):
        if os.getenv(key, "").strip():
            return True
    return False


def main(*, force: bool = False) -> None:
    del force  # idempotent ingest; reserved for future wipe semantics
    if _urls_configured():
        seed_log(
            "presupuesto_corpus",
            "PRESUPUESTO_ABIERTO_DOWNLOAD_URLS set — use gasto ingest --source presupuesto_abierto --live",
        )
        raise SystemExit(
            "presupuesto_corpus: offline profile skips when download URLs are configured"
        )

    manifest = load_offline_manifest()
    paths = list_offline_corpus_paths()
    if not paths:
        raise SystemExit("presupuesto_corpus: no offline corpus files found")

    seed_log(
        "presupuesto_corpus",
        f"manifest v={manifest.get('version')} files={len(paths)} (URLs empty → offline)",
    )

    Session = sessionmaker(bind=make_engine(DATABASE_URL), autoflush=False, autocommit=False)
    session = Session()
    skip_storage = seed_skip_storage()
    skip_alerts = seed_skip_alerts_during_ingest()
    total = 0
    try:
        result = run_ingest(
            session,
            "presupuesto_abierto",
            fixture_path=str(FIXTURE_DIR),
            live=False,
            skip_storage=skip_storage,
            skip_alerts=skip_alerts,
        )
        session.commit()
        total = int(result.get("records") or 0)
        seed_log("presupuesto_corpus", f"ingest rows={total} status={result.get('status')}")
        if total < 1:
            raise SystemExit("presupuesto_corpus: expected budget rows from offline corpus")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    seed_log("presupuesto_corpus", "complete")


if __name__ == "__main__":
    main()
