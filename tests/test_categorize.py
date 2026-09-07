from common.categorize import CATEGORIES, categorize, normalize_category


def test_categorize_salud():
    assert categorize(object_description="Equipamiento hospitalario UCI") == "salud"


def test_categorize_obras():
    assert categorize(object_description="Construcción de aulas y obras viales") == "educacion"


def test_categorize_consultoria():
    assert categorize(object_description="Consultoría POA 2025") == "consultoria"


def test_categorize_otros():
    assert categorize(object_description="") == "otros"
    assert normalize_category("nope") == "otros"


def test_catalog_complete():
    assert "obras" in CATEGORIES and "otros" in CATEGORIES
