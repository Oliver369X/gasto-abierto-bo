#!/usr/bin/env python3
"""Offline AURA Incendios demo data (ledger, expedientes, territorios).

  docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile fire_demo
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def main() -> None:
    legacy = ROOT / "scripts" / "_legacy" / "seed_fire_2024.py"
    if not legacy.exists():
        raise SystemExit("fire_demo: missing scripts/_legacy/seed_fire_2024.py")
    sys.path.insert(0, str(ROOT / "packages"))
    sys.path.insert(0, str(ROOT / "services"))
    # Reuse battle-tested offline fire corpus (fixtures only).
    import runpy

    saved_argv = sys.argv
    try:
        sys.argv = [str(legacy)]
        runpy.run_path(str(legacy), run_name="__main__")
    finally:
        sys.argv = saved_argv
