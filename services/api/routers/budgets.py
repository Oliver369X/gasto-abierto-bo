"""Budget aggregation and correlation endpoints."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.deps import RATE, get_db, limiter
from api.schemas import BudgetAggregateOut, BudgetTotalsOut
from common.data_quality import public_budget_filter
from schema.models import BudgetLine, Entity

router = APIRouter()

GroupBy = Literal["entity", "department", "year", "category", "program"]


def _execution_ratio(current: Decimal, executed: Decimal) -> float | None:
    if current > 0:
        return float(executed / current * 100)
    return None


@router.get("/v1/budgets/totals", response_model=BudgetTotalsOut, tags=["budgets"])
@limiter.limit(f"{RATE}/minute")
def budget_totals(
    request: Request,
    db: Session = Depends(get_db),
    year: Optional[int] = None,
    quality: str = Query("public", pattern="^(public|all)$"),
) -> BudgetTotalsOut:
    """Headline presupuesto totals — vigente, ejecutado, ratio."""
    base = public_budget_filter(BudgetLine) if quality == "public" else BudgetLine.is_current.is_(True)
    stmt = select(
        func.count(BudgetLine.id),
        func.coalesce(func.sum(BudgetLine.current_amount), 0),
        func.coalesce(func.sum(BudgetLine.executed_amount), 0),
        func.coalesce(func.sum(BudgetLine.payment), 0),
    ).where(base)
    if year is not None:
        stmt = stmt.where(BudgetLine.year == year)
    lines, cur, exe, pay = db.execute(stmt).one()
    cur_d = Decimal(cur or 0)
    pay_d = Decimal(pay or 0) if pay else Decimal(exe or 0)
    years = list(
        db.scalars(
            select(BudgetLine.year).where(base).distinct().order_by(BudgetLine.year.desc())
        ).all()
    )
    return BudgetTotalsOut(
        lines=int(lines or 0),
        current_total=cur_d,
        executed_total=Decimal(exe or 0),
        payment_total=pay_d,
        execution_ratio_pct=_execution_ratio(cur_d, pay_d),
        years=[int(y) for y in years if y is not None],
        source_id="presupuesto_abierto",
    )


@router.get("/v1/budgets/aggregate", response_model=list[BudgetAggregateOut], tags=["budgets"])
@limiter.limit(f"{RATE}/minute")
def budget_aggregate(
    request: Request,
    db: Session = Depends(get_db),
    group_by: GroupBy = Query("department"),
    year: Optional[int] = None,
    quality: str = Query("public", pattern="^(public|all)$"),
    limit: int = Query(25, ge=1, le=100),
) -> list[BudgetAggregateOut]:
    """Aggregate budget lines by institution, department, year, category or program."""
    base = public_budget_filter(BudgetLine) if quality == "public" else BudgetLine.is_current.is_(True)

    if group_by == "year":
        stmt = (
            select(
                BudgetLine.year,
                func.count(BudgetLine.id),
                func.coalesce(func.sum(BudgetLine.current_amount), 0),
                func.coalesce(func.sum(BudgetLine.executed_amount), 0),
                func.count(func.distinct(BudgetLine.entity_id)),
            )
            .where(base)
            .group_by(BudgetLine.year)
            .order_by(BudgetLine.year.desc())
            .limit(limit)
        )
        rows = db.execute(stmt).all()
        return [
            BudgetAggregateOut(
                key=str(y),
                label=str(y),
                lines=int(n or 0),
                current_total=Decimal(cur or 0),
                executed_total=Decimal(exe or 0),
                entity_count=int(ent or 0),
                execution_ratio_pct=_execution_ratio(Decimal(cur or 0), Decimal(exe or 0)),
                year=int(y),
                group_by=group_by,
            )
            for y, n, cur, exe, ent in rows
        ]

    if group_by == "entity":
        stmt = (
            select(
                Entity.id,
                Entity.name,
                func.count(BudgetLine.id),
                func.coalesce(func.sum(BudgetLine.current_amount), 0),
                func.coalesce(func.sum(BudgetLine.executed_amount), 0),
            )
            .select_from(BudgetLine)
            .join(Entity, BudgetLine.entity_id == Entity.id)
            .where(base)
            .group_by(Entity.id, Entity.name)
            .order_by(func.coalesce(func.sum(BudgetLine.current_amount), 0).desc())
            .limit(limit)
        )
        if year is not None:
            stmt = stmt.where(BudgetLine.year == year)
        rows = db.execute(stmt).all()
        return [
            BudgetAggregateOut(
                key=str(eid),
                label=name,
                lines=int(n or 0),
                current_total=Decimal(cur or 0),
                executed_total=Decimal(exe or 0),
                entity_count=1,
                execution_ratio_pct=_execution_ratio(Decimal(cur or 0), Decimal(exe or 0)),
                year=year,
                group_by=group_by,
                href=f"/entidad/{eid}",
            )
            for eid, name, n, cur, exe in rows
        ]

    if group_by == "department":
        dept = func.coalesce(Entity.department, "Sin departamento")
        stmt = (
            select(
                dept,
                func.count(BudgetLine.id),
                func.coalesce(func.sum(BudgetLine.current_amount), 0),
                func.coalesce(func.sum(BudgetLine.executed_amount), 0),
                func.count(func.distinct(BudgetLine.entity_id)),
            )
            .select_from(BudgetLine)
            .join(Entity, BudgetLine.entity_id == Entity.id)
            .where(base)
            .group_by(dept)
            .order_by(func.coalesce(func.sum(BudgetLine.current_amount), 0).desc())
            .limit(limit)
        )
        if year is not None:
            stmt = stmt.where(BudgetLine.year == year)
        rows = db.execute(stmt).all()
        return [
            BudgetAggregateOut(
                key=str(key),
                label=str(key),
                lines=int(n or 0),
                current_total=Decimal(cur or 0),
                executed_total=Decimal(exe or 0),
                entity_count=int(ent or 0),
                execution_ratio_pct=_execution_ratio(Decimal(cur or 0), Decimal(exe or 0)),
                year=year,
                group_by=group_by,
            )
            for key, n, cur, exe, ent in rows
        ]

    if group_by == "category":
        cat = func.coalesce(BudgetLine.category, "sin_categoria")
        stmt = (
            select(
                cat,
                func.count(BudgetLine.id),
                func.coalesce(func.sum(BudgetLine.current_amount), 0),
                func.coalesce(func.sum(BudgetLine.executed_amount), 0),
                func.count(func.distinct(BudgetLine.entity_id)),
            )
            .where(base)
            .group_by(cat)
            .order_by(func.coalesce(func.sum(BudgetLine.current_amount), 0).desc())
            .limit(limit)
        )
        if year is not None:
            stmt = stmt.where(BudgetLine.year == year)
        rows = db.execute(stmt).all()
        return [
            BudgetAggregateOut(
                key=str(key),
                label=str(key),
                lines=int(n or 0),
                current_total=Decimal(cur or 0),
                executed_total=Decimal(exe or 0),
                entity_count=int(ent or 0),
                execution_ratio_pct=_execution_ratio(Decimal(cur or 0), Decimal(exe or 0)),
                year=year,
                group_by=group_by,
            )
            for key, n, cur, exe, ent in rows
        ]

    # program
    prog = func.coalesce(BudgetLine.program_project, "Sin programa")
    stmt = (
        select(
            prog,
            func.count(BudgetLine.id),
            func.coalesce(func.sum(BudgetLine.current_amount), 0),
            func.coalesce(func.sum(BudgetLine.executed_amount), 0),
            func.count(func.distinct(BudgetLine.entity_id)),
        )
        .where(base)
        .group_by(prog)
        .order_by(func.coalesce(func.sum(BudgetLine.current_amount), 0).desc())
        .limit(limit)
    )
    if year is not None:
        stmt = stmt.where(BudgetLine.year == year)
    rows = db.execute(stmt).all()
    return [
        BudgetAggregateOut(
            key=str(key)[:120],
            label=str(key)[:120],
            lines=int(n or 0),
            current_total=Decimal(cur or 0),
            executed_total=Decimal(exe or 0),
            entity_count=int(ent or 0),
            execution_ratio_pct=_execution_ratio(Decimal(cur or 0), Decimal(exe or 0)),
            year=year,
            group_by=group_by,
        )
        for key, n, cur, exe, ent in rows
    ]
