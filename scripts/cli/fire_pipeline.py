"""Backward-compatible entry: python -m scripts.cli.fire_pipeline """
from __future__ import annotations

import sys

from scripts.cli.fire import _cmd_pipeline


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="AURA Incendios fire pipeline")
    parser.add_argument("--phase", required=True, help="f1..f13 or all")
    parser.add_argument("--no-artifact", action="store_true")
    args = parser.parse_args(argv)
    return _cmd_pipeline(args)


if __name__ == "__main__":
    raise SystemExit(main())
