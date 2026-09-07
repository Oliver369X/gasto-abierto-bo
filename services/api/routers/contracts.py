"""Contract list/get + claims + evidence."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.deps import RATE, get_db, limiter
from api.errors import not_found
from api.schemas import ClaimEvidenceOut, ClaimOut, ContractOut
from common.categorize import normalize_category
from common.claims import claims_for_contract
from common.data_quality import PUBLIC_BLOCKED_QUALITIES
from schema.models import Claim, ClaimEvidence, Contract

router = APIRouter()


@router.get("/v1/contracts", response_model=list[ContractOut], tags=["contracts"])
@limiter.limit(f"{RATE}/minute")
def list_contracts(
    request: Request,
    db: Session = Depends(get_db),
    entity: Optional[int] = None,
    supplier: Optional[int] = None,
    q: Optional[str] = None,
    modality: Optional[str] = None,
    category: Optional[str] = None,
    source_id: Optional[str] = None,
    year: Optional[int] = None,
    min_amount: Optional[Decimal] = None,
    max_amount: Optional[Decimal] = None,
    include_history: bool = False,
    quality: str = Query("public", pattern="^(public|all)$"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[Contract]:
    stmt = select(Contract)
    if not include_history:
        stmt = stmt.where(Contract.is_current.is_(True))
    if quality == "public":
        stmt = stmt.where(
            Contract.is_synthetic.is_(False),
            (Contract.source_quality.is_(None))
            | (~Contract.source_quality.in_(list(PUBLIC_BLOCKED_QUALITIES))),
        )
    if entity is not None:
        stmt = stmt.where(Contract.entity_id == entity)
    if supplier is not None:
        stmt = stmt.where(Contract.supplier_id == supplier)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            (Contract.object_description.ilike(like)) | (Contract.cuce.ilike(like))
        )
    if modality:
        stmt = stmt.where(Contract.modality.ilike(f"%{modality}%"))
    if category:
        stmt = stmt.where(Contract.category == normalize_category(category))
    if source_id:
        stmt = stmt.where(Contract.source_id == source_id)
    if year is not None:
        stmt = stmt.where(func.extract("year", Contract.contract_date) == year)
    if min_amount is not None:
        stmt = stmt.where(Contract.amount >= min_amount)
    if max_amount is not None:
        stmt = stmt.where(Contract.amount <= max_amount)
    stmt = stmt.order_by(Contract.contract_date.desc().nullslast()).offset(offset).limit(limit)
    return list(db.scalars(stmt).all())


@router.get("/v1/contracts/{contract_id}", response_model=ContractOut, tags=["contracts"])
@limiter.limit(f"{RATE}/minute")
def get_contract(request: Request, contract_id: int, db: Session = Depends(get_db)) -> Contract:
    row = db.get(Contract, contract_id)
    if not row:
        raise not_found("Contrato")
    return row


@router.get("/v1/contracts/{contract_id}/claims", response_model=list[ClaimOut], tags=["evidence"])
@limiter.limit(f"{RATE}/minute")
def contract_claims(
    request: Request, contract_id: int, db: Session = Depends(get_db)
) -> list[Claim]:
    if not db.get(Contract, contract_id):
        raise not_found("Contrato")
    return claims_for_contract(db, contract_id)


@router.get(
    "/v1/contracts/{contract_id}/evidence",
    response_model=list[ClaimEvidenceOut],
    tags=["evidence"],
)
@limiter.limit(f"{RATE}/minute")
def contract_evidence(
    request: Request, contract_id: int, db: Session = Depends(get_db)
) -> list[ClaimEvidence]:
    if not db.get(Contract, contract_id):
        raise not_found("Contrato")
    claim_ids = [
        c.id
        for c in db.scalars(
            select(Claim).where(Claim.entity_type == "contract", Claim.entity_id == contract_id)
        ).all()
    ]
    if not claim_ids:
        return []
    return list(
        db.scalars(select(ClaimEvidence).where(ClaimEvidence.claim_id.in_(claim_ids))).all()
    )
