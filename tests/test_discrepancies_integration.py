"""Integration tests for cross-source discrepancies after reconcile."""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from common.cross_source import discrepancies_from_cuce_groups, group_contracts_by_cuce


def test_reconcile_fixture_overlap_produces_discrepancies():
    """Mirrors sicoes/contracts_overlap_agetic.csv vs agetic CUCE pairs."""
    rows = [
        SimpleNamespace(
            id=1,
            cuce="OCDS-2019-001",
            source_id="agetic",
            amount=Decimal("1000000"),
            entity_id=1,
        ),
        SimpleNamespace(
            id=2,
            cuce="OCDS-2019-001",
            source_id="sicoes",
            amount=Decimal("1150000"),
            entity_id=1,
        ),
    ]
    groups = group_contracts_by_cuce(rows)
    discs = discrepancies_from_cuce_groups(groups)
    assert len(discs) >= 1
    assert discs[0]["source_a"] != discs[0]["source_b"]
