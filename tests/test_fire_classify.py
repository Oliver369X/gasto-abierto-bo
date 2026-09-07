"""Tests for fire spending classifier."""
from decimal import Decimal

from common.fire.classify import (
    attribution_amount,
    classify_fire_text,
    infer_cycle,
    is_fire_related,
)


def test_direct_aircraft_rental():
    r = classify_fire_text(
        object_description="Alquiler de aeronave para lucha contra incendios forestales"
    )
    assert r.attribution == "directo"
    assert r.cycle == "respuesta"
    assert r.confidence_score >= Decimal("0.9")
    assert is_fire_related(r)


def test_direct_bomberos():
    r = classify_fire_text(object_description="Movilización de bomberos forestales Santa Cruz")
    assert r.attribution == "directo"
    assert "bomberos forestales" in " ".join(r.matched_terms) or any(
        "bombero" in t for t in r.matched_terms
    )


def test_generic_emergency_not_fire():
    """Critical: emergencia/desastre alone must NOT inflate the fire ledger."""
    r = classify_fire_text(
        object_description="Contratación por emergencia y desastres — ayuda humanitaria general",
        modality="Emergencia / Desastre",
    )
    assert r.attribution == "no_relacionado"
    assert r.reason == "emergencia_generica_sin_incendio"
    assert not is_fire_related(r)


def test_flood_emergency_not_fire():
    r = classify_fire_text(
        object_description="Atención de emergencia por inundaciones en Beni"
    )
    assert r.attribution == "no_relacionado"


def test_probable_cisterna():
    r = classify_fire_text(
        object_description="Adquisición de cisterna para operaciones de emergencia"
    )
    # "cisterna" is probable; may also hit emergencia genérica — cisterna is in PROBABLE
    assert r.attribution in ("probable", "no_relacionado")
    # With cisterna keyword it should be probable before generic check... 
    # Actually order: DIRECT first, then PROBABLE, then GENERIC. cisterna is in PROBABLE.
    assert r.attribution == "probable"


def test_cycle_prevencion():
    assert infer_cycle("Construcción de cortafuegos y monitoreo de focos de calor") == "prevencion"


def test_cycle_preparacion():
    assert infer_cycle("Adquisición de EPP y motobomba para brigadas") == "preparacion"


def test_cycle_recuperacion():
    assert infer_cycle("Programa de reforestación post incendio forestal") == "recuperacion"


def test_empty_text():
    r = classify_fire_text()
    assert r.attribution == "no_relacionado"


def test_force_direct():
    r = classify_fire_text(force_direct=True)
    assert r.attribution == "directo"
    assert r.classification_method == "human_verified"


def test_attribution_amount_parcial():
    amt = attribution_amount(
        amount=Decimal("1000.00"),
        attribution="parcial",
        partial_ratio=Decimal("0.40"),
    )
    assert amt == Decimal("400.00")


def test_attribution_amount_indirecto_excluded():
    assert attribution_amount(amount=Decimal("500"), attribution="indirecto") == Decimal("0")
