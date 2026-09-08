"""Infer administrative level and department from public entity names."""
from __future__ import annotations

from common.mefp_geo import infer_department_mefp


def infer_entity_level(name: str | None) -> str:
    n = (name or "").lower()
    if any(k in n for k in ("gam ", "alcaldía", "alcaldia", "municipal", " municipio")):
        return "municipal"
    if any(k in n for k in ("gad ", "gobernación", "gobernacion", "departamental")):
        return "departamental"
    return "nacional"


def infer_department(
    name: str | None,
    level: str | None = None,
    *,
    ubicacion: str | None = None,
) -> str | None:
    mefp = infer_department_mefp(name, ubicacion)
    if mefp:
        return mefp
    n = (name or "").lower()
    for needle, dept in (
        ("santa cruz", "Santa Cruz"),
        ("cochabamba", "Cochabamba"),
        ("la paz", "La Paz"),
        ("oruro", "Oruro"),
        ("potosí", "Potosí"),
        ("potosi", "Potosí"),
        ("chuquisaca", "Chuquisaca"),
        ("tarija", "Tarija"),
        ("beni", "Beni"),
        ("pando", "Pando"),
    ):
        if needle in n:
            return dept
    if level == "departamental" and " de " in n:
        tail = n.split(" de ")[-1].strip().title()
        if tail and len(tail) > 2:
            return tail
    return None
