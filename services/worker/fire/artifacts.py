"""Write versioned JSON artifacts under data/extracted/."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
EXTRACTED = ROOT / "data" / "extracted"


def write_json(name: str, payload: dict[str, Any] | list[Any], *, subdir: str | None = None) -> Path:
    base = EXTRACTED / subdir if subdir else EXTRACTED
    base.mkdir(parents=True, exist_ok=True)
    path = base / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def extracted_root() -> Path:
    EXTRACTED.mkdir(parents=True, exist_ok=True)
    return EXTRACTED
