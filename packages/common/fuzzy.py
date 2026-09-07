from __future__ import annotations

import re
import unicodedata
from typing import Sequence

from rapidfuzz import fuzz, process


_NON_ALNUM = re.compile(r"[^a-z0-9\s]")
_SPACES = re.compile(r"\s+")

_REPLACEMENTS = [
    (r"\bgobierno autonomo municipal\b", "gam"),
    (r"\bgobierno autonomo departamental\b", "gad"),
    (r"\bgob\.\s*auton\.\s*mun\.\b", "gam"),
    (r"\bmunicipio de\b", "gam"),
    (r"\balcaldia de\b", "gam"),
    (r"\bgobernacion de\b", "gad"),
    (r"\bministerio de\b", "min"),
    (r"\bs\.?r\.?l\.?\b", "srl"),
    (r"\bs\.?a\.?\b", "sa"),
]


def canonicalize_name(name: str | None) -> str:
    if not name:
        return ""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().strip()
    for pattern, repl in _REPLACEMENTS:
        s = re.sub(pattern, repl, s)
    s = _NON_ALNUM.sub(" ", s)
    s = _SPACES.sub(" ", s).strip()
    return s


def best_match(
    query: str,
    candidates: Sequence[str],
    *,
    score_cutoff: int = 85,
) -> tuple[str, float] | None:
    if not query or not candidates:
        return None
    q = canonicalize_name(query)
    canon_map = {canonicalize_name(c): c for c in candidates}
    keys = list(canon_map.keys())
    result = process.extractOne(q, keys, scorer=fuzz.token_set_ratio, score_cutoff=score_cutoff)
    if not result:
        return None
    matched_key, score, _ = result
    return canon_map[matched_key], float(score)
