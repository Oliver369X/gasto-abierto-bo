"""Link-strength helpers for money↔ops↔event (anti-cartesian)."""
from __future__ import annotations

import re

ALLOWED_STRENGTHS = frozenset(
    {
        "CONFIRMADO",
        "FUERTEMENTE_VINCULADO",
        "PROBABLE",
        "POSIBLE",
        "NO_DETERMINABLE",
    }
)

AERO_OPS_KEYS = re.compile(
    r"(operacion(?:es)?_?a[eé]rea|descarga|helic[oó]ptero|aeronave|aviaci[oó]n|"
    r"bambi|guardian|horas?_?vuelo|medios_aereos)",
    re.I,
)
AERO_TEXT = re.compile(r"aeronave|helic[oó]ptero|aviaci[oó]n|bambi|guardian|descarga", re.I)


def infer_strength(
    *,
    same_year: bool,
    event_linked: bool,
    explicit_reference: bool,
) -> str:
    if explicit_reference:
        return "CONFIRMADO"
    if same_year and event_linked:
        return "PROBABLE"
    if same_year:
        return "POSIBLE"
    return "NO_DETERMINABLE"


def normalize_strength(value: str | None) -> str:
    v = (value or "NO_DETERMINABLE").upper()
    return v if v in ALLOWED_STRENGTHS else "NO_DETERMINABLE"


def is_aerial_ops_blob(text: str) -> bool:
    return bool(AERO_OPS_KEYS.search(text) or AERO_TEXT.search(text))
