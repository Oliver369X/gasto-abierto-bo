#!/usr/bin/env python3
"""Legacy entrypoint — delegates to worker.gasto.seeds.fire_demo_impl.

Prefer: python -m scripts.cli gasto seed --profile fire_demo
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(ROOT / "services"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    from worker.gasto.seeds.fire_demo_impl import main as seed_main

    seed_main(force=args.force)


if __name__ == "__main__":
    main()
