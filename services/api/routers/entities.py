"""Entities, budgets, history, and entity activity."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.deps import RATE, get_db, limiter
from api.errors import not_found
from api.schemas import (
    ActivityItem,
    BudgetOut,
    EntityOut,
    YearAggOut,
    YearCompareOut,
)
from common.data_quality import public_budget_filter, public_contract_filter
from common.discrepancy import delta_pct
from schema.models import Alert, AuditReport, BudgetLine, Contract, Discrepancy, Entity

router = APIRouter()


@router.get("/v1/entities", response_model=list[EntityOut], tags=["entities"])
@limiter.limit(f"{RATE}/minute")
def list_entities(
    request: Request,
    db: Session = Depends(get_db),
    q: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[Entity]:
    stmt = select(Entity).order_by(Entity.name)
    if q:
        stmt = stmt.where(Entity.name.ilike(f"%{q}%"))
    if level:
        stmt = stmt.where(Entity.level == level)
    return list(db.scalars(stmt.offset(offset).limit(limit)).all())


@router.get("/v1/entities/{entity_id}", response_model=EntityOut, tags=["entities"])
@limiter.limit(f"{RATE}/minute")
def get_entity(request: Request, entity_id: int, db: Session = Depends(get_db)) -> Entity:
    row = db.get(Entity, entity_id)
    if not row:
        raise not_found("Entidad")
    return row


@router.get("/v1/budgets", response_model=list[BudgetOut], tags=["budgets"])
@limiter.limit(f"{RATE}/minute")
def list_budgets(
    request: Request,
    db: Session = Depends(get_db),
    entity_id: Optional[int] = None,
    year: Optional[int] = None,
    include_history: bool = False,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[BudgetLine]:
    stmt = select(BudgetLine)
    if not include_history:
        stmt = stmt.where(BudgetLine.is_current.is_(True))
    if entity_id is not None:
        stmt = stmt.where(BudgetLine.entity_id == entity_id)
    if year is not None:
        stmt = stmt.where(BudgetLine.year == year)
    return list(
        db.scalars(stmt.order_by(BudgetLine.year.desc()).offset(offset).limit(limit)).all()
    )


@router.get("/v1/history/years", response_model=list[YearAggOut], tags=["history"])
@limiter.limit(f"{RATE}/minute")
def history_by_year(
    request: Request,
    db: Session = Depends(get_db),
    entity_id: Optional[int] = None,
    quality: str = Query("public", pattern="^(public|all)$"),
) -> list[YearAggOut]:
    """Aggregate contracts + budgets by calendar/management year (2019+)."""
    years = set()
    c_base = public_contract_filter(Contract) if quality == "public" else Contract.is_current.is_(True)
    b_base = public_budget_filter(BudgetLine) if quality == "public" else BudgetLine.is_current.is_(True)
    c_stmt = select(func.extract("year", Contract.contract_date)).where(
        c_base, Contract.contract_date.is_not(None)
    )
    b_stmt = select(BudgetLine.year).where(b_base)
    if entity_id is not None:
        c_stmt = c_stmt.where(Contract.entity_id == entity_id)
        b_stmt = b_stmt.where(BudgetLine.entity_id == entity_id)
    for y in db.scalars(c_stmt.distinct()).all():
        if y is not None:
            years.add(int(y))
    for y in db.scalars(b_stmt.distinct()).all():
        years.add(int(y))

    out: list[YearAggOut] = []
    for year in sorted(years):
        c_q = select(
            func.count(Contract.id),
            func.coalesce(func.sum(Contract.amount), 0),
        ).where(
            c_base,
            func.extract("year", Contract.contract_date) == year,
        )
        b_q = select(
            func.count(BudgetLine.id),
            func.coalesce(func.sum(BudgetLine.current_amount), 0),
            func.coalesce(func.sum(BudgetLine.executed_amount), 0),
        ).where(b_base, BudgetLine.year == year)
        if entity_id is not None:
            c_q = c_q.where(Contract.entity_id == entity_id)
            b_q = b_q.where(BudgetLine.entity_id == entity_id)
        c_count, c_amt = db.execute(c_q).one()
        b_count, b_cur, b_exe = db.execute(b_q).one()
        out.append(
            YearAggOut(
                year=year,
                contracts=int(c_count or 0),
                contract_amount=Decimal(c_amt or 0),
                budget_lines=int(b_count or 0),
                budget_current_total=Decimal(b_cur or 0),
                budget_executed_total=Decimal(b_exe or 0),
            )
        )
    return out


def _year_slice(db: Session, year: int, entity_id: Optional[int] = None) -> tuple[int, Decimal, Decimal]:
    c_q = select(
        func.count(Contract.id),
        func.coalesce(func.sum(Contract.amount), 0),
    ).where(
        public_contract_filter(Contract),
        func.extract("year", Contract.contract_date) == year,
    )
    b_q = select(func.coalesce(func.sum(BudgetLine.current_amount), 0)).where(
        public_budget_filter(BudgetLine), BudgetLine.year == year
    )
    if entity_id is not None:
        c_q = c_q.where(Contract.entity_id == entity_id)
        b_q = b_q.where(BudgetLine.entity_id == entity_id)
    c_count, c_amt = db.execute(c_q).one()
    b_cur = db.execute(b_q).scalar() or 0
    return int(c_count or 0), Decimal(c_amt or 0), Decimal(b_cur or 0)


@router.get("/v1/history/compare", response_model=YearCompareOut, tags=["history"])
@limiter.limit(f"{RATE}/minute")
def history_compare(
    request: Request,
    db: Session = Depends(get_db),
    year_a: int = Query(..., ge=2000, le=2100),
    year_b: int = Query(..., ge=2000, le=2100),
    entity_id: Optional[int] = None,
) -> YearCompareOut:
    ca, aa, ba = _year_slice(db, year_a, entity_id)
    cb, ab, bb = _year_slice(db, year_b, entity_id)
    return YearCompareOut(
        year_a=year_a,
        year_b=year_b,
        contracts_a=ca,
        contracts_b=cb,
        contracts_delta_pct=delta_pct(Decimal(ca), Decimal(cb)),
        amount_a=aa,
        amount_b=ab,
        amount_delta_pct=delta_pct(aa, ab),
        budget_current_a=ba,
        budget_current_b=bb,
        budget_delta_pct=delta_pct(ba, bb),
    )


@router.get("/v1/entities/{entity_id}/activity", response_model=list[ActivityItem], tags=["entities"])
@limiter.limit(f"{RATE}/minute")
def entity_activity(
    request: Request,
    entity_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(40, ge=1, le=100),
) -> list[ActivityItem]:
    if not db.get(Entity, entity_id):
        raise not_found("Entidad")
    items: list[ActivityItem] = []
    for c in db.scalars(
        select(Contract)
        .where(Contract.entity_id == entity_id, Contract.is_current.is_(True))
        .order_by(Contract.contract_date.desc().nullslast())
        .limit(limit)
    ).all():
        items.append(
            ActivityItem(
                kind="contract",
                title=c.cuce or c.object_description or f"Contrato #{c.id}",
                at=c.contract_date.isoformat() if c.contract_date else None,
                href=f"/contrato/{c.id}",
                meta={"amount": str(c.amount) if c.amount is not None else None, "category": c.category},
            )
        )
    for b in db.scalars(
        select(BudgetLine)
        .where(BudgetLine.entity_id == entity_id, BudgetLine.is_current.is_(True))
        .order_by(BudgetLine.year.desc())
        .limit(limit)
    ).all():
        items.append(
            ActivityItem(
                kind="budget",
                title=f"Presupuesto gestión {b.year}",
                at=str(b.year),
                href=None,
                meta={"current": str(b.current_amount) if b.current_amount is not None else None},
            )
        )
    for a in db.scalars(
        select(Alert).where(Alert.entity_id == entity_id).order_by(Alert.created_at.desc()).limit(limit)
    ).all():
        items.append(
            ActivityItem(
                kind="alert",
                title=a.title,
                at=a.created_at.isoformat() if a.created_at else None,
                href=f"/alertas/{a.id}",
                meta={"severity": a.severity, "rule_id": a.rule_id},
            )
        )
    for d in db.scalars(
        select(Discrepancy).where(Discrepancy.entity_id == entity_id).limit(limit)
    ).all():
        items.append(
            ActivityItem(
                kind="discrepancy",
                title=d.concept,
                at=d.created_at.isoformat() if d.created_at else None,
                href=f"/discrepancias#disc-{d.id}",
                meta={"source_a": d.source_a, "source_b": d.source_b},
            )
        )
    for au in db.scalars(
        select(AuditReport).where(AuditReport.entity_id == entity_id).limit(limit)
    ).all():
        items.append(
            ActivityItem(
                kind="audit",
                title=au.title,
                at=str(au.year) if au.year else None,
                href=f"/auditorias/{au.id}",
                meta={},
            )
        )
    return items[:limit]
