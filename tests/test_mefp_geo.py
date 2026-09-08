from common.entity_geo import infer_department
from common.mefp_geo import (
    classify_ubicacion,
    infer_department_mefp,
    target_ubicacion_count,
    ubicacion_count,
)


def test_infer_department_uses_mefp_gam_alias():
    assert infer_department("GAM Santa Cruz de la Sierra") == "Santa Cruz"
    assert infer_department("GAM La Paz") == "La Paz"


def test_classify_ubicacion_municipal():
    hit = classify_ubicacion("GAM Cochabamba")
    assert hit is not None
    assert hit["department"] == "Cochabamba"
    assert hit["level"] == "municipal"


def test_mefp_incremental_coverage():
    count = ubicacion_count()
    target = target_ubicacion_count()
    assert count >= 200
    assert target == 352
    assert count < target


def test_mefp_fire_municipalities():
    """Santa Cruz fire-affected municipios from seed corpus."""
    hit = classify_ubicacion("Gobierno Autónomo Municipal de San Matías")
    assert hit is not None
    assert hit["department"] == "Santa Cruz"
    assert hit["level"] == "municipal"


def test_infer_department_mefp_expanded():
    assert infer_department_mefp("GAM Guayaramerín", None) == "Beni"
    assert infer_department_mefp(None, "Villazón") == "Potosí"
    assert infer_department_mefp("GAM Vallegrande", None) == "Santa Cruz"
    assert infer_department_mefp(None, "Tarabuco") == "Chuquisaca"


def test_mefp_wave5_municipal_sample():
    hit = classify_ubicacion("GAM San Javier")
    assert hit is not None
    assert hit["department"] == "Santa Cruz"
    assert hit["name"] == "San Javier"


def test_mefp_wave6_municipal_sample():
    hit = classify_ubicacion("GAM Okinawa")
    assert hit is not None
    assert hit["department"] == "Santa Cruz"
    assert hit["name"] == "Okinawa"
    assert infer_department_mefp("GAM Atocha", None) == "Potosí"


def test_mefp_unique_codes():
    from common.mefp_geo import load_ubicaciones

    codes = [u["code"] for u in load_ubicaciones()]
    assert len(codes) == len(set(codes))
