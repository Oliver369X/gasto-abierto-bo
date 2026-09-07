#!/usr/bin/env python3
"""Deprecated — use: python -m scripts.cli gasto ingest ..."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "packages"), str(ROOT / "services"), str(ROOT)]
print("DEPRECATED: use python -m scripts.cli gasto ingest --source … --sync", file=sys.stderr)

# Re-export for any leftover imports
from worker.gasto.ingest_cli import SOURCES, enqueue, main, sync_ingest  # noqa: E402

if __name__ == "__main__":
    main()
