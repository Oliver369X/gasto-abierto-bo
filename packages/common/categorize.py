"""Keyword-based gasto categories for Bolivia (MVP — not ML)."""
from __future__ import annotations

import re
from typing import Optional

CATEGORIES: tuple[str, ...] = (
    "obras",
    "salud",
    "educacion",
    "servicios",
    "bienes",
    "consultoria",
    "otros",
)

CATEGORY_LABELS: dict[str, str] = {
    "obras": "Obras",
    "salud": "Salud",
    "educacion": "Educación",
    "servicios": "Servicios",
    "bienes": "Bienes",
    "consultoria": "Consultoría",
    "otros": "Otros",
}

# Order matters: first match wins.
_RULES: list[tuple[str, re.Pattern[str]]] = [
    (
        "salud",
        re.compile(
            r"\b(salud|hospital|medic|farmac|uci|insumo\s*m[eé]dic|ambulator|cl[ií]nic)",
            re.I,
        ),
    ),
    (
        "educacion",
        re.compile(
            r"\b(educaci[oó]n|escuela|colegio|aula|universidad|estudiante|docente)",
            re.I,
        ),
    ),
    (
        "obras",
        re.compile(
            r"\b(obra|construcci[oó]n|vial|carretera|puente|paviment|infraestructur|"
            r"edificaci[oó]n|remodelaci[oó]n|se[nñ]alizaci[oó]n)",
            re.I,
        ),
    ),
    (
        "consultoria",
        re.compile(r"\b(consultor[ií]a|asesor[ií]a|estudio\s+t[eé]cnic|dise[nñ]o)", re.I),
    ),
    (
        "servicios",
        re.compile(
            r"\b(servicio|limpieza|mantenimiento|vigilancia|seguridad|transporte|"
            r"alquiler|arrendamiento)",
            re.I,
        ),
    ),
    (
        "bienes",
        re.compile(
            r"\b(bienes|equipo|mobiliario|computador|suministro|adquisici[oó]n|"
            r"compra\s+de|veh[ií]culo)",
            re.I,
        ),
    ),
]


def categorize(
    *,
    object_description: str | None = None,
    modality: str | None = None,
    budget_item: str | None = None,
    program_project: str | None = None,
) -> str:
    """Return one of CATEGORIES based on free-text fields."""
    blob = " ".join(
        x for x in (object_description, modality, budget_item, program_project) if x
    )
    if not blob.strip():
        return "otros"
    for cat, pattern in _RULES:
        if pattern.search(blob):
            return cat
    # modality heuristics
    mod = (modality or "").lower()
    if "directa" in mod or "menor" in mod:
        return "servicios"
    return "otros"


def normalize_category(value: Optional[str]) -> str:
    if not value:
        return "otros"
    v = value.strip().lower()
    return v if v in CATEGORIES else "otros"
