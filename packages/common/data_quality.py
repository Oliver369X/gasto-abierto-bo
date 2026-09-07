"""Data quality gates for public gasto aggregates (Plan G1)."""
from __future__ import annotations

from typing import Any

from sqlalchemy import and_, not_, or_
from sqlalchemy.sql import ColumnElement

SYNTHETIC_QUALITIES = frozenset({"SYNTHETIC", "PLACEHOLDER"})
PUBLIC_BLOCKED_QUALITIES = SYNTHETIC_QUALITIES


def is_public_row(row: Any) -> bool:
    """Whether a core row may enter public totals / alerts."""
    if getattr(row, "is_synthetic", False):
        return False
    q = (getattr(row, "source_quality", None) or "").upper()
    if q in PUBLIC_BLOCKED_QUALITIES:
        return False
    return True


def public_contract_filter(model: Any) -> ColumnElement[bool]:
    """SQLAlchemy filter for public-facing contract queries.

    is_synthetic is the hard gate; source_quality SYNTHETIC/PLACEHOLDER
    is always paired with is_synthetic=True in backfill/classify_origin.
    """
    return and_(
        model.is_current.is_(True),
        model.is_synthetic.is_(False),
    )


def public_budget_filter(model: Any) -> ColumnElement[bool]:
    return and_(
        model.is_current.is_(True),
        model.is_synthetic.is_(False),
    )


def classify_origin(
    *,
    source_id: str,
    cuce: str | None = None,
    source_note: str | None = None,
) -> dict[str, Any]:
    """Deterministic quality labels for ingest/backfill."""
    sid = (source_id or "").lower()
    note = (source_note or "").lower()
    cuce_u = (cuce or "").upper()

    if sid == "seed" or "fixture" in note or "placeholder" in note:
        return {
            "is_synthetic": True,
            "is_official": False,
            "is_inferred": False,
            "source_quality": "SYNTHETIC",
            "evidence_status": "none",
            "confidence_score": 0.0,
            "data_origin": "seed",
        }
    if cuce_u.startswith("GA-DEEP-") or "deep" in note:
        return {
            "is_synthetic": True,
            "is_official": False,
            "is_inferred": False,
            "source_quality": "SYNTHETIC",
            "evidence_status": "none",
            "confidence_score": 0.0,
            "data_origin": "seed",
        }
    if "ocp" in note or "datos.gob.bo" in note or "ocds" in note:
        return {
            "is_synthetic": False,
            "is_official": True,
            "is_inferred": False,
            "source_quality": "OFFICIAL_UNVERIFIED",
            "evidence_status": "linked",
            "confidence_score": 0.7,
            "data_origin": "ocds",
        }
    if sid == "agetic" and not note.startswith("sociedatos"):
        # OCDS / CKAN packages — treat as official open data unless marked seed
        return {
            "is_synthetic": False,
            "is_official": True,
            "is_inferred": False,
            "source_quality": "OFFICIAL_UNVERIFIED",
            "evidence_status": "partial",
            "confidence_score": 0.65,
            "data_origin": "ocds",
        }
    if "sociedatos" in note or "lab-tecnosocial" in note or sid == "sicoes":
        return {
            "is_synthetic": False,
            "is_official": False,
            "is_inferred": False,
            "source_quality": "OFFICIAL_UNVERIFIED",
            "evidence_status": "partial",
            "confidence_score": 0.55,
            "data_origin": "civic_mirror",
        }
    if sid in ("presupuesto_abierto", "cge", "gad_scz", "gam_scz"):
        return {
            "is_synthetic": False,
            "is_official": False,
            "is_inferred": False,
            "source_quality": "PARTIAL",
            "evidence_status": "partial",
            "confidence_score": 0.5,
            "data_origin": "civic_mirror",
        }
    return {
        "is_synthetic": False,
        "is_official": False,
        "is_inferred": True,
        "source_quality": "INFERRED",
        "evidence_status": "none",
        "confidence_score": 0.3,
        "data_origin": "inferred",
    }


QUALITY_COLUMNS = (
    "is_synthetic",
    "is_official",
    "is_inferred",
    "source_quality",
    "evidence_status",
    "confidence_score",
    "data_origin",
    "source_note",
)
