"""Capability asset classification from expenditure titles (F10)."""
from __future__ import annotations

import re
from typing import Any

_AERO_RENT = re.compile(r"alquiler.+(aeronave|helic[oó]ptero)|helic[oó]ptero.+alquiler", re.I)
_GUARDIAN = re.compile(r"guardian|contenedor(?:es)?\s+a[eé]reo|bambi", re.I)
_EPP = re.compile(r"\bepp\b|batefuego|mochila\s+(?:forestal|aspersora)|equipo\s+de\s+protecci", re.I)
_CISTERNA = re.compile(r"cisterna", re.I)
_BRIGADA = re.compile(r"brigada|brigadista", re.I)
_RENT = re.compile(r"alquiler|arrendamiento", re.I)


def classify_asset(title: str) -> dict[str, Any]:
    t = title or ""
    if _AERO_RENT.search(t) or (
        re.search(r"aeronave|helic[oó]ptero", t, re.I) and _RENT.search(t)
    ):
        return {
            "asset_type": "aeronave",
            "ownership": "rented",
            "is_preventive": False,
        }
    if _GUARDIAN.search(t):
        return {
            "asset_type": "sistema_aereo",
            "ownership": "purchased",
            "is_preventive": True,
        }
    if _EPP.search(t):
        return {
            "asset_type": "epp",
            "ownership": "purchased",
            "is_preventive": True,
        }
    if _CISTERNA.search(t):
        rented = bool(_RENT.search(t))
        return {
            "asset_type": "cisterna",
            "ownership": "rented" if rented else "purchased",
            "is_preventive": not rented,
        }
    if _BRIGADA.search(t):
        return {
            "asset_type": "brigada",
            "ownership": "owned",
            "is_preventive": True,
        }
    return {
        "asset_type": "other",
        "ownership": "unknown",
        "is_preventive": False,
    }
