from common.fire.geo_bbox import assign_department


def test_assigns_ola_departments_from_coordinates():
    assert assign_department(-17.78, -63.18) == "Santa Cruz"
    assert assign_department(-14.83, -64.90) == "Beni"
    assert assign_department(-11.02, -68.75) == "Pando"


def test_returns_none_outside_supported_boxes():
    assert assign_department(-16.50, -68.15) is None
