#!/usr/bin/env python3
"""Thin wrapper — logic lives in worker.gasto.verify."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(ROOT / "services"))

from worker.gasto.verify import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
