from decimal import Decimal
from types import SimpleNamespace

from common.cross_source import (
    budget_vs_contracts_discrepancy,
    discrepancies_from_cuce_groups,
    group_contracts_by_cuce,
)


def test_group_and_discrepancy_across_sources():
    rows = [
        SimpleNamespace(id=1, cuce="ocds-2019-001", source_id="agetic", amount=Decimal("100"), entity_id=1),
        SimpleNamespace(id=2, cuce="OCDS-2019-001", source_id="sicoes", amount=Decimal("150"), entity_id=1),
        SimpleNamespace(id=3, cuce="OCDS-2020-001", source_id="agetic", amount=Decimal("10"), entity_id=2),
    ]
    groups = group_contracts_by_cuce(rows)
    assert "OCDS-2019-001" in groups
    discs = discrepancies_from_cuce_groups(groups)
    assert len(discs) == 1
    assert discs[0]["source_a"] in ("agetic", "sicoes")
    assert discs[0]["delta_pct"] and discs[0]["delta_pct"] > 0


def test_budget_vs_contracts_tolerance():
    assert (
        budget_vs_contracts_discrepancy(
            entity_id=1,
            year=2024,
            budget_executed=Decimal("100"),
            contracts_sum=Decimal("105"),
            budget_source="presupuesto_abierto",
            tolerance_pct=Decimal("15"),
        )
        is None
    )
    d = budget_vs_contracts_discrepancy(
        entity_id=1,
        year=2024,
        budget_executed=Decimal("100"),
        contracts_sum=Decimal("200"),
        budget_source="presupuesto_abierto",
        tolerance_pct=Decimal("15"),
    )
    assert d is not None
    assert d["concept"].startswith("budget_vs_contracts:")
