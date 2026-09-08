"""MEFP Presupuesto Abierto geographic classifier (incremental toward 352 ubicaciones).

Wave 4 ships 100+ curated departments + municipalities aligned with fixtures and
contract history. Expand by merging the official GeoPackage/CSV ubicaciones export
from https://abierto.economiayfinanzas.gob.bo/descargas into
packages/common/data/mefp_ubicaciones.json (see scripts/ops/expand_mefp_wave5.py
and docs/sources/mefp_ubicaciones.md).
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent / "data" / "mefp_ubicaciones.json"


def _norm(text: str | None) -> str:
    if not text:
        return ""
    s = unicodedata.normalize("NFKD", text)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


@lru_cache(maxsize=1)
def load_ubicaciones() -> list[dict]:
    if not DATA_PATH.exists():
        return []
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return list(data.get("ubicaciones") or [])


def ubicacion_count() -> int:
    return len(load_ubicaciones())


def target_ubicacion_count() -> int:
    if DATA_PATH.exists():
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        return int(data.get("target_total") or 352)
    return 352


def classify_ubicacion(text: str | None) -> dict | None:
    """Return best MEFP ubicacion match for free-text department/location field."""
    needle = _norm(text)
    if not needle:
        return None
    best: dict | None = None
    best_len = 0
    for row in load_ubicaciones():
        candidates: list[str] = []
        name = row.get("name")
        if isinstance(name, str) and name.strip():
            candidates.append(name)
        for alias in row.get("aliases") or []:
            if isinstance(alias, str) and alias.strip():
                candidates.append(alias)
        for alias in candidates:
            a = _norm(alias)
            if not a or len(a) < 3:
                continue
            if a == needle or a in needle or needle in a:
                if len(a) > best_len:
                    best = row
                    best_len = len(a)
    return best


def infer_department_mefp(name: str | None, ubicacion: str | None = None) -> str | None:
    """Infer department using MEFP ubicaciones, then entity name."""
    for field in (ubicacion, name):
        hit = classify_ubicacion(field)
        if hit and hit.get("department"):
            return hit["department"]
    return None


def infer_municipality_mefp(name: str | None, ubicacion: str | None = None) -> str | None:
    for field in (ubicacion, name):
        hit = classify_ubicacion(field)
        if hit and hit.get("level") == "municipal":
            return hit.get("name")
    return None
