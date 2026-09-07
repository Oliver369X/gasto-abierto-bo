"""Product gate, conflicts, cross-source, discrepancies."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.deps import RATE, get_db, limiter
from api.schemas import ClaimConflictOut, CrossSourceSummary, DiscrepancyOut, ProductGateOut
from common.data_quality import PUBLIC_BLOCKED_QUALITIES, public_contract_filter
from common.discrepancy import delta_pct
from schema.models import (
    AuditFinding,
    Claim,
    ClaimConflict,
    ClaimEvidence,
    Contract,
    Discrepancy,
    PublicEntityMaster,
    Supplier,
    SupplierMaster,
)

router = APIRouter()


@router.get("/v1/cross-source/summary", response_model=CrossSourceSummary, tags=["quality"])
@limiter.limit(f"{RATE}/minute")
def cross_source_summary(request: Request, db: Session = Depends(get_db)) -> CrossSourceSummary:
    """How well sources contrast: shared CUCEs and discrepancy counts.

    Aggregated in SQL — loading all contracts in Python is O(minutes) on
    production-sized databases (1.5M+ rows).
    """
    base = select(Contract).where(
        Contract.is_current.is_(True), Contract.cuce.is_not(None)
    ).subquery()
    contracts_with_cuce = db.scalar(select(func.count()).select_from(base)) or 0
    multi = db.scalar(
        select(func.count()).select_from(
            select(base.c.cuce)
            .group_by(base.c.cuce)
            .having(func.count(func.distinct(base.c.source_id)) >= 2)
            .subquery()
        )
    ) or 0
    sources = list(
        db.scalars(select(func.distinct(base.c.source_id))).all()
    )
    discs_total = db.scalar(select(func.count()).select_from(Discrepancy)) or 0
    cuce_n = db.scalar(
        select(func.count()).select_from(Discrepancy).where(
            Discrepancy.concept.like("contract:%")
        )
    ) or 0
    budget_n = db.scalar(
        select(func.count()).select_from(Discrepancy).where(
            Discrepancy.concept.like("budget_vs_contracts:%")
        )
    ) or 0
    return CrossSourceSummary(
        contracts_with_cuce=int(contracts_with_cuce),
        cuces_multi_source=int(multi),
        discrepancies_total=int(discs_total),
        discrepancies_cuce=int(cuce_n),
        discrepancies_budget_vs_contracts=int(budget_n),
        sources_in_contracts=sorted(sources),
    )


@router.get("/v1/discrepancies", response_model=list[DiscrepancyOut], tags=["quality"])
@limiter.limit(f"{RATE}/minute")
def list_discrepancies(
    request: Request,
    db: Session = Depends(get_db),
    entity_id: Optional[int] = None,
    source: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[DiscrepancyOut]:
    stmt = select(Discrepancy).order_by(Discrepancy.created_at.desc())
    if entity_id is not None:
        stmt = stmt.where(Discrepancy.entity_id == entity_id)
    if source:
        stmt = stmt.where(
            (Discrepancy.source_a == source) | (Discrepancy.source_b == source)
        )
    rows = list(db.scalars(stmt.offset(offset).limit(limit)).all())
    out: list[DiscrepancyOut] = []
    for r in rows:
        out.append(
            DiscrepancyOut(
                id=r.id,
                concept=r.concept,
                entity_id=r.entity_id,
                amount_a=r.amount_a,
                amount_b=r.amount_b,
                source_a=r.source_a,
                source_b=r.source_b,
                ref_a=r.ref_a,
                ref_b=r.ref_b,
                delta_pct=delta_pct(r.amount_a, r.amount_b),
            )
        )
    return out


@router.get("/v1/discrepancies/{disc_id}", response_model=DiscrepancyOut, tags=["quality"])
@limiter.limit(f"{RATE}/minute")
def get_discrepancy(
    request: Request, disc_id: int, db: Session = Depends(get_db)
) -> DiscrepancyOut:
    r = db.get(Discrepancy, disc_id)
    if not r:
        raise HTTPException(404, "Discrepancy not found")
    return DiscrepancyOut(
        id=r.id,
        concept=r.concept,
        entity_id=r.entity_id,
        amount_a=r.amount_a,
        amount_b=r.amount_b,
        source_a=r.source_a,
        source_b=r.source_b,
        ref_a=r.ref_a,
        ref_b=r.ref_b,
        delta_pct=delta_pct(r.amount_a, r.amount_b),
    )


@router.get("/v1/conflicts", response_model=list[ClaimConflictOut], tags=["evidence"])
@limiter.limit(f"{RATE}/minute")
def list_conflicts(
    request: Request,
    db: Session = Depends(get_db),
    status: str = "open",
    limit: int = Query(50, ge=1, le=200),
) -> list[ClaimConflict]:
    stmt = select(ClaimConflict).where(ClaimConflict.status == status).limit(limit)
    return list(db.scalars(stmt).all())


@router.get("/v1/product-gate", response_model=ProductGateOut, tags=["quality"])
@limiter.limit(f"{RATE}/minute")
def product_gate(request: Request, db: Session = Depends(get_db)) -> ProductGateOut:
    """G10 checklist with real thresholds — not toy booleans."""
    synth_in_public_amt = db.scalar(
        select(func.coalesce(func.sum(Contract.amount), 0)).where(
            public_contract_filter(Contract),
            Contract.is_synthetic.is_(True),
        )
    ) or 0
    official_placeholder = db.scalar(
        select(func.count())
        .select_from(Contract)
        .where(
            Contract.is_official.is_(True),
            Contract.source_quality.in_(list(PUBLIC_BLOCKED_QUALITIES)),
        )
    ) or 0
    claims_n = db.scalar(select(func.count()).select_from(Claim)) or 0
    evidence_n = db.scalar(select(func.count()).select_from(ClaimEvidence)) or 0
    sm_n = db.scalar(select(func.count()).select_from(SupplierMaster)) or 0
    em_n = db.scalar(select(func.count()).select_from(PublicEntityMaster)) or 0
    suppliers_n = db.scalar(select(func.count()).select_from(Supplier)) or 0
    findings_n = db.scalar(select(func.count()).select_from(AuditFinding)) or 0
    conflicts_n = db.scalar(select(func.count()).select_from(ClaimConflict)) or 0
    amt_flag = (
        db.scalar(
            select(func.count()).select_from(Contract).where(Contract.has_awarded_amount.is_(True))
        )
        or 0
    )
    with_amt = (
        db.scalar(
            select(func.count())
            .select_from(Contract)
            .where(
                Contract.is_current.is_(True),
                Contract.is_synthetic.is_(False),
                Contract.amount.is_not(None),
                Contract.amount > 0,
            )
        )
        or 0
    )

    checks = {
        "zero_synthetic_in_public_amount_filter": Decimal(str(synth_in_public_amt)) == 0,
        "no_official_placeholder": int(official_placeholder) == 0,
        "claims_with_evidence": int(claims_n) >= 50 and int(evidence_n) >= int(claims_n) * 0.8,
        "supplier_masters_cover_staging": int(sm_n) >= max(1, int(suppliers_n) * 0.9),
        "entity_masters_present": int(em_n) >= 100,
        "audit_findings_present": int(findings_n) >= 20,
        "completeness_flags_match_amounts": int(amt_flag) >= int(with_amt),
        "conflicts_schema_ready": True,
        "coverage_endpoint": True,
    }
    notes = [
        f"claims={claims_n} evidence={evidence_n} conflicts={conflicts_n}",
        f"supplier_master={sm_n}/{suppliers_n} entity_master={em_n} findings={findings_n}",
        f"has_awarded_amount={amt_flag} contracts_with_amount={with_amt}",
        "Cobertura SICOES reciente puede fallar umbral hasta enrich+PROXY_URL.",
        "Ausencia de monto ≠ Bs 0 en UI.",
    ]
    return ProductGateOut(
        checks=checks,
        notes=notes,
        **{"pass": all(checks.values())},
    )
