from decimal import Decimal

from common.dates import parse_date_flexible
from common.discrepancy import build_discrepancy
from common.fuzzy import best_match, canonicalize_name
from common.money import parse_money


def test_parse_money_bo():
    assert parse_money("1.200.000,50") == Decimal("1200000.50")
    assert parse_money("Bs 50.000") == Decimal("50000")
    assert parse_money("1,200,000.50") == Decimal("1200000.50")


def test_canonicalize_and_match():
    a = canonicalize_name("Gobierno Autónomo Municipal de La Paz")
    b = canonicalize_name("GAM La Paz")
    assert "gam" in a and "gam" in b
    match = best_match("GAM La Paz", ["Gobierno Autónomo Municipal de La Paz", "Ministerio de Educación"])
    assert match is not None
    assert "La Paz" in match[0]


def test_parse_date():
    assert parse_date_flexible("15/03/2026").isoformat() == "2026-03-15"


def test_discrepancy():
    d = build_discrepancy(
        concept="x",
        entity_id=1,
        amount_a=Decimal("10"),
        amount_b=Decimal("20"),
        source_a="a",
        source_b="b",
    )
    assert d is not None
    assert build_discrepancy(
        concept="x",
        entity_id=1,
        amount_a=Decimal("10"),
        amount_b=Decimal("10"),
        source_a="a",
        source_b="b",
    ) is None
