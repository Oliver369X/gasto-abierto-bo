from common.entity_geo import infer_department, infer_entity_level


def test_infer_entity_level():
    assert infer_entity_level("GAM Santa Cruz de la Sierra") == "municipal"
    assert infer_entity_level("GAD Santa Cruz") == "departamental"
    assert infer_entity_level("Ministerio de Educación") == "nacional"


def test_infer_department():
    assert infer_department("GAM Santa Cruz de la Sierra") == "Santa Cruz"
    assert infer_department("GAD Santa Cruz", "departamental") == "Santa Cruz"
    assert infer_department("GAM La Paz") == "La Paz"
    assert infer_department("Ministerio de Educación") is None
