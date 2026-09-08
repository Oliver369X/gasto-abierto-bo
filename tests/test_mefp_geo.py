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
    assert count >= 20
    assert target == 352
    assert count < target
