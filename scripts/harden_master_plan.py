#!/usr/bin/env python3
"""Deprecated — use: python -m scripts.cli gasto harden"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "packages"), str(ROOT / "services"), str(ROOT)]
print("DEPRECATED: use python -m scripts.cli gasto harden", file=sys.stderr)
from worker.gasto.harden import main  # noqa: E402

if __name__ == "__main__":
    main()
