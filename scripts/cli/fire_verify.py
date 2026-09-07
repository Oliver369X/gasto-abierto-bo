"""CLI: verify AURA Incendios Plan 2 gates."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "packages"), str(ROOT / "services"), str(ROOT)]


def main(argv: list[str] | None = None) -> int:
    from worker.fire.verification.plan2 import main as verify_main

    return int(verify_main())


if __name__ == "__main__":
    raise SystemExit(main())
