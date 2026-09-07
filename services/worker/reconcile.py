from __future__ import annotations

"""DB-level cross-source reconciliation (CUCE + budget vs contracts)."""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from common.cross_source import (
    budget_vs_contracts_discrepancy,
    discrepancies_from_cuce_groups,
    group_contracts_by_cuce,
)
from schema.models import BudgetLine, Contract, Discrepancy, Entity


def _existing_keys(session: Session) -> set[tuple]:
    rows = session.execute(
        select(
            Discrepancy.concept,
            Discrepancy.source_a,
            Discrepancy.source_b,
            Discrepancy.ref_a,
            Discrepancy.ref_b,
        )
    ).all()
    return {(r[0], r[1], r[2], r[3], r[4]) for r in rows}


def reconcile_cuce(session: Session) -> int:
    contracts = list(
        session.scalars(
            select(Contract).where(Contract.is_current.is_(True), Contract.cuce.is_not(None))
        ).all()
    )
    groups = group_contracts_by_cuce(contracts)
    existing = _existing_keys(session)
    added = 0
    for disc in discrepancies_from_cuce_groups(groups):
        key = (
            disc["concept"],
            disc["source_a"],
            disc["source_b"],
            disc.get("ref_a"),
            disc.get("ref_b"),
        )
        # also accept swapped sources
        key2 = (
            disc["concept"],
            disc["source_b"],
            disc["source_a"],
            disc.get("ref_b"),
            disc.get("ref_a"),
        )
        if key in existing or key2 in existing:
            continue
        payload = {k: v for k, v in disc.items() if k != "delta_pct"}
        session.add(Discrepancy(**payload))
        existing.add(key)
        added += 1
    return added


def reconcile_budget_vs_contracts(session: Session, *, tolerance_pct: Decimal = Decimal("15")) -> int:
    existing = _existing_keys(session)
    added = 0
    budgets = list(
        session.scalars(
            select(BudgetLine).where(BudgetLine.is_current.is_(True))
        ).all()
    )
    for b in budgets:
        if b.executed_amount is None:
            continue
        contracts_sum = session.scalar(
            select(func.coalesce(func.sum(Contract.amount), 0)).where(
                Contract.is_current.is_(True),
                Contract.entity_id == b.entity_id,
                func.extract("year", Contract.contract_date) == b.year,
            )
        )
        contracts_sum = Decimal(contracts_sum or 0)
        if contracts_sum <= 0:
            continue
        disc = budget_vs_contracts_discrepancy(
            entity_id=b.entity_id,
            year=b.year,
            budget_executed=b.executed_amount,
            contracts_sum=contracts_sum,
            budget_source=b.source_id,
            tolerance_pct=tolerance_pct,
        )
        if not disc:
            continue
        key = (
            disc["concept"],
            disc["source_a"],
            disc["source_b"],
            disc.get("ref_a"),
            disc.get("ref_b"),
        )
        if key in existing:
            continue
        payload = {k: v for k, v in disc.items() if k != "delta_pct"}
        session.add(Discrepancy(**payload))
        existing.add(key)
        added += 1
    return added


def reconcile_all(session: Session) -> dict:
    cuce_n = reconcile_cuce(session)
    budget_n = reconcile_budget_vs_contracts(session)
    entities = session.scalar(select(func.count()).select_from(Entity)) or 0
    return {
        "cuce_discrepancies": cuce_n,
        "budget_vs_contracts": budget_n,
        "entities": entities,
    }
