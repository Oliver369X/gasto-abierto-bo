"""O6.1 — classify_asset title → asset_type / ownership / is_preventive."""
from __future__ import annotations

import pytest

from common.fire.capability import classify_asset

CASES = [
    ("Servicio de alquiler de aeronave para incendios", "aeronave", "rented", False),
    ("Alquiler de helicóptero forestal 2024", "aeronave", "rented", False),
    ("Sistema Guardian / contenedor aéreo", "sistema_aereo", "purchased", True),
    ("Adquisición de bambi bucket", "sistema_aereo", "purchased", True),
    ("Kit EPP para brigadistas forestales", "epp", "purchased", True),
    ("Mochila aspersora y batefuego", "epp", "purchased", True),
    ("Compra de cisterna contra incendios", "cisterna", "purchased", True),
    ("Alquiler de cisterna de emergencia", "cisterna", "rented", False),
    ("Conformación de brigada forestal permanente", "brigada", "owned", True),
    ("Pago a brigadistas en temporada", "brigada", "owned", True),
    ("Compra de útiles de oficina", "other", "unknown", False),
    ("Servicio de catering institucional", "other", "unknown", False),
]


@pytest.mark.parametrize("title,asset_type,ownership,is_preventive", CASES)
def test_classify_asset_table(title, asset_type, ownership, is_preventive):
    result = classify_asset(title)
    assert result["asset_type"] == asset_type
    assert result["ownership"] == ownership
    assert result["is_preventive"] is is_preventive
