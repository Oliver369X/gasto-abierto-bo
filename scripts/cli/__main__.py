"""Unified CLI: python -m scripts.cli {gasto|fire} ..."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "packages"), str(ROOT / "services"), str(ROOT)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.cli",
        description="Gasto Abierto BO — CLI oficial (gasto + fire)",
    )
    sub = parser.add_subparsers(dest="domain", required=True)

    from scripts.cli.gasto import register as register_gasto
    from scripts.cli.fire import register as register_fire

    register_gasto(sub.add_parser("gasto", help="Ingesta, seed, harden, verify, enrich"))
    register_fire(sub.add_parser("fire", help="Pipeline y verificación AURA Incendios"))

    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 2
    return int(handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
