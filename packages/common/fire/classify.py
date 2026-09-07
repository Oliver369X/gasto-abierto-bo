"""Deterministic classifier for fire-related public spending (MVP — no ML)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

ATTRIBUTIONS = (
    "directo",
    "probable",
    "parcial",
    "indirecto",
    "no_relacionado",
)

CYCLES = ("prevencion", "preparacion", "respuesta", "recuperacion")

ATTRIBUTION_LABELS: dict[str, str] = {
    "directo": "Directo",
    "probable": "Probable",
    "parcial": "Parcial",
    "indirecto": "Indirecto",
    "no_relacionado": "No relacionado",
}

CYCLE_LABELS: dict[str, str] = {
    "prevencion": "Prevención",
    "preparacion": "Preparación",
    "respuesta": "Respuesta",
    "recuperacion": "Recuperación",
}

# Explicit fire vocabulary — order matters for cycle hints.
_DIRECT_FIRE = re.compile(
    r"(incendio\s*forestal|incendios\s*forestales|lucha\s+contra\s+(?:el\s+)?incendio|"
    r"combate\s+(?:de|a|al)\s+(?:los\s+)?incendios?|bomberos?\s+forestales?|"
    r"brigada(?:s)?\s+forestal(?:es)?|brigadista(?:s)?|"
    r"sofocaci[oó]n\s+(?:de\s+)?incendios?|liquidaci[oó]n\s+de\s+incendios?|"
    r"emergencia\s+(?:[ií]gnea|forestal)|desastre\s+forestal|"
    r"alquiler\s+de\s+aeronave|alquiler\s+de\s+helic[oó]ptero|"
    r"avi[oó]n\s+cisterna|bambi\s*bucket|sistema\s+guardian|cajas?\s+guardian|"
    r"contenedores?\s+a[eé]reos?\s+contraincendios|"
    r"descarga(?:s)?\s+de\s+agua|focos?\s+de\s+calor|"
    r"quemas?\s+(?:ilegales|controladas)|l[ií]nea\s+de\s+defensa|"
    r"cortafuego(?:s)?|mochila(?:s)?\s+(?:forestal|aspersora))",
    re.I,
)

_PROBABLE_FIRE = re.compile(
    r"(equipo\s+forestal|mochila\s+forestal|batefuego|motobomba|"
    r"epp(?:\s+forestal)?|equipo\s+de\s+protecci[oó]n\s+personal|"
    r"cisterna|maquinaria\s+pesada.*emergencia|"
    r"combustible\s+(?:para\s+)?(?:emergencia|maquinaria|a[eé]reo)|"
    r"v[ií]veres\s+(?:para\s+)?bomberos|alimentaci[oó]n\s+de\s+brigadistas|"
    r"operaciones?\s+a[eé]reas?|helic[oó]ptero|aeronave|"
    r"fuego\b|quemad)",
    re.I,
)

_PARTIAL_FIRE = re.compile(
    r"(?=.*\b(?:incendios?|fuego|quemad(?:a|as|o|os)?|quemas?)\b)"
    r"(?=.*\b(?:inundaci[oó]n|inundaciones|sequ[ií]a|heladas?|granizo|"
    r"deslizamientos?|sismo|sanitaria|multiamenaza|multi-evento)\b)",
    re.I,
)

_INDIRECT_FIRE = re.compile(
    r"(fortalecimiento\s+(?:institucional|del\s+centro)|"
    r"sistema\s+de\s+alerta\s+temprana\s+multiamenaza|"
    r"centro\s+de\s+monitoreo\s+de\s+riesgos|"
    r"equipamiento\s+de\s+unidad\s+de\s+gesti[oó]n\s+de\s+riesgo|"
    r"plataforma\s+de\s+coordinaci[oó]n\s+para\s+emergencias|"
    r"base\s+log[ií]stica\s+multiprop[oó]sito|"
    r"capacidad\s+municipal\s+para\s+reducci[oó]n\s+de\s+riesgos|"
    r"comunicaciones\s+para\s+gesti[oó]n\s+integral\s+de\s+riesgos|"
    r"infraestructura\s+institucional\s+de\s+respuesta\s+multiamenaza)",
    re.I,
)

# Generic emergency/disaster without fire keywords — must NOT auto-attribute.
_GENERIC_EMERGENCY = re.compile(
    r"\b(emergencia|desastre|ayuda\s+humanitaria|contrataci[oó]n\s+por\s+emergencia)\b",
    re.I,
)

_CYCLE_RULES: list[tuple[str, re.Pattern[str]]] = [
    (
        "prevencion",
        re.compile(
            r"(prevenci[oó]n|monitoreo|cortafuego|cortafuegos|brigada\s+preventiva|"
            r"capacitaci[oó]n|campa[nñ]a|focos?\s+de\s+calor|quemas?\s+controladas)",
            re.I,
        ),
    ),
    (
        "preparacion",
        re.compile(
            r"(adquisici[oó]n|compra|equipamiento|veh[ií]culo|cisterna|"
            r"base\s+operativa|epp|motobomba|mochila\s+forestal)",
            re.I,
        ),
    ),
    (
        "recuperacion",
        re.compile(
            r"(reforestaci[oó]n|restauraci[oó]n|rehabilitaci[oó]n|reconstrucci[oó]n|"
            r"ayuda\s+humanitaria)",
            re.I,
        ),
    ),
    (
        "respuesta",
        re.compile(
            r"(alquiler\s+de\s+aeronave|helic[oó]ptero|combate|sofocaci[oó]n|"
            r"bomberos|descarga|combustible|operaci[oó]n|emergencia\s+forestal|"
            r"lucha\s+contra)",
            re.I,
        ),
    ),
]


@dataclass(frozen=True)
class FireClassification:
    attribution: str
    confidence_score: Decimal
    cycle: str
    classification_method: str
    matched_terms: list[str]
    reason: str
    rules_fired: tuple[str, ...] = ()
    evidence_span: str | None = None


def _collect_matches(pattern: re.Pattern[str], text: str) -> list[str]:
    return sorted({m.group(0).lower() for m in pattern.finditer(text)})


def infer_cycle(text: str) -> str:
    for cycle, pattern in _CYCLE_RULES:
        if pattern.search(text):
            return cycle
    return "respuesta"


def classify_fire_text(
    *,
    object_description: str | None = None,
    modality: str | None = None,
    program_project: str | None = None,
    title: str | None = None,
    force_direct: bool = False,
) -> FireClassification:
    """Classify whether a spending item relates to forest fires.

    Important: generic 'emergencia/desastre' without fire vocabulary is
    ``no_relacionado`` (or at most ignored) — never auto-attributed as fire spend.
    """
    parts = [object_description or "", modality or "", program_project or "", title or ""]
    text = " ".join(p for p in parts if p).strip()
    if not text and not force_direct:
        return FireClassification(
            attribution="no_relacionado",
            confidence_score=Decimal("1.000"),
            cycle="respuesta",
            classification_method="exact_keyword",
            matched_terms=[],
            reason="sin_texto",
            rules_fired=("empty_text",),
        )

    if force_direct or _DIRECT_FIRE.search(text):
        terms = _collect_matches(_DIRECT_FIRE, text) if text else ["human_verified"]
        m = _DIRECT_FIRE.search(text) if text else None
        return FireClassification(
            attribution="directo",
            confidence_score=Decimal("1.000") if force_direct else Decimal("0.950"),
            cycle=infer_cycle(text) if text else "respuesta",
            classification_method="human_verified" if force_direct else "exact_keyword",
            matched_terms=terms,
            reason="vocabulario_explicito_incendio",
            rules_fired=("direct_fire_vocab", "force_direct") if force_direct else ("direct_fire_vocab",),
            evidence_span=(m.group(0) if m else None),
        )

    if _PARTIAL_FIRE.search(text):
        terms = _collect_matches(_PARTIAL_FIRE, text)
        return FireClassification(
            attribution="parcial",
            confidence_score=Decimal("0.600"),
            cycle=infer_cycle(text),
            classification_method="exact_keyword",
            matched_terms=terms,
            reason="programa_multi_evento_con_componente_incendio",
            rules_fired=("partial_fire_nonfire_mix",),
            evidence_span=text[:240],
        )

    if _PROBABLE_FIRE.search(text):
        terms = _collect_matches(_PROBABLE_FIRE, text)
        m = _PROBABLE_FIRE.search(text)
        return FireClassification(
            attribution="probable",
            confidence_score=Decimal("0.700"),
            cycle=infer_cycle(text),
            classification_method="exact_keyword",
            matched_terms=terms,
            reason="vocabulario_probable_incendio",
            rules_fired=("probable_fire_vocab",),
            evidence_span=(m.group(0) if m else None),
        )

    if _INDIRECT_FIRE.search(text):
        terms = _collect_matches(_INDIRECT_FIRE, text)
        m = _INDIRECT_FIRE.search(text)
        return FireClassification(
            attribution="indirecto",
            confidence_score=Decimal("0.450"),
            cycle=infer_cycle(text),
            classification_method="exact_keyword",
            matched_terms=terms,
            reason="capacidad_general_gestion_riesgos",
            rules_fired=("indirect_fire_capacity",),
            evidence_span=(m.group(0) if m else None),
        )

    if _GENERIC_EMERGENCY.search(text):
        return FireClassification(
            attribution="no_relacionado",
            confidence_score=Decimal("0.900"),
            cycle="respuesta",
            classification_method="exact_keyword",
            matched_terms=_collect_matches(_GENERIC_EMERGENCY, text),
            reason="emergencia_generica_sin_incendio",
            rules_fired=("generic_emergency_block",),
            evidence_span=_GENERIC_EMERGENCY.search(text).group(0),
        )

    return FireClassification(
        attribution="no_relacionado",
        confidence_score=Decimal("0.850"),
        cycle="respuesta",
        classification_method="exact_keyword",
        matched_terms=[],
        reason="sin_indicios_incendio",
        rules_fired=("default_no_relacionado",),
    )


def is_fire_related(result: FireClassification) -> bool:
    return result.attribution in ("directo", "probable", "parcial", "indirecto")


def attribution_amount(
    *,
    amount: Decimal | None,
    attribution: str,
    partial_ratio: Decimal | None = None,
) -> Optional[Decimal]:
    if amount is None:
        return None
    if attribution == "no_relacionado":
        return Decimal("0")
    if attribution == "parcial":
        ratio = partial_ratio if partial_ratio is not None else Decimal("0.50")
        return (amount * ratio).quantize(Decimal("0.01"))
    if attribution == "indirecto":
        return Decimal("0")  # capacity spend — exclude from "verificable" totals
    return amount
