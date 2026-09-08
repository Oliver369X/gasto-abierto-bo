#!/usr/bin/env python3
"""Staging seed: history + presupuesto_corpus + fire_demo + harden in one command.

Use after `docker compose up` on staging/VPS before `make staging-check`:

  docker compose run --rm --entrypoint python api \\
    -m scripts.cli gasto seed --profile staging

Equivalent to running the four profiles in order without publish/deep corpus.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(ROOT / "services"))

from worker.gasto.seeds._helpers import seed_log


def main(*, force: bool = False) -> None:
    if not os.getenv("DATABASE_URL"):
        raise SystemExit("staging: DATABASE_URL required")

    seed_log("staging", "history (multi-año offline)")
    from worker.gasto.seeds import history

    history.main()

    seed_log("staging", "presupuesto_corpus (offline manifest)")
    from worker.gasto.seeds import presupuesto_corpus

    presupuesto_corpus.main(force=force)

    seed_log("staging", "fire_demo (AURA incendios)")
    from worker.gasto.seeds import fire_demo

    fire_demo.main(force=force)

    seed_log("staging", "harden (masters / claims / findings)")
    from worker.gasto.harden_impl import main as harden_main

    harden_main()

    seed_log("staging", "complete — run make staging-check")
    print("Seed staging OK", flush=True)


if __name__ == "__main__":
    main()
