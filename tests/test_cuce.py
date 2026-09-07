from common.cuce import normalize_cuce


def test_normalize_cuce_variants():
    assert normalize_cuce("ocds-2019-001") == "OCDS-2019-001"
    assert normalize_cuce("OCDS 2019/001") == "OCDS-2019-001"
    assert normalize_cuce("  OCDS-2019-001  ") == "OCDS-2019-001"
    assert normalize_cuce("") is None
    assert normalize_cuce(None) is None
