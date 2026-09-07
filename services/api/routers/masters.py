"""Supplier/entity masters and merge candidates."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import RATE, get_db, limiter
from api.errors import not_found
from api.schemas import EntityMasterOut, MergeCandidateOut, SupplierMasterOut
from schema.models import EntityAlias, MergeCandidate, PublicEntityMaster, SupplierAlias, SupplierMaster

router = APIRouter()


@router.get("/v1/supplier-masters/{master_id}", response_model=SupplierMasterOut, tags=["suppliers"])
@limiter.limit(f"{RATE}/minute")
def get_supplier_master(
    request: Request, master_id: int, db: Session = Depends(get_db)
) -> SupplierMaster:
    row = db.get(SupplierMaster, master_id)
    if not row:
        raise not_found("Proveedor maestro")
    return row


@router.get("/v1/supplier-masters/{master_id}/aliases", response_model=list[str], tags=["suppliers"])
@limiter.limit(f"{RATE}/minute")
def supplier_master_aliases(
    request: Request, master_id: int, db: Session = Depends(get_db)
) -> list[str]:
    if not db.get(SupplierMaster, master_id):
        raise not_found("Proveedor maestro")
    return [
        a.alias
        for a in db.scalars(
            select(SupplierAlias).where(SupplierAlias.supplier_master_id == master_id)
        ).all()
    ]


@router.get("/v1/entity-masters/{master_id}", response_model=EntityMasterOut, tags=["entities"])
@limiter.limit(f"{RATE}/minute")
def get_entity_master(
    request: Request, master_id: int, db: Session = Depends(get_db)
) -> PublicEntityMaster:
    row = db.get(PublicEntityMaster, master_id)
    if not row:
        raise not_found("Entidad maestra")
    return row


@router.get("/v1/entity-masters/{master_id}/aliases", response_model=list[str], tags=["entities"])
@limiter.limit(f"{RATE}/minute")
def entity_master_aliases(
    request: Request, master_id: int, db: Session = Depends(get_db)
) -> list[str]:
    if not db.get(PublicEntityMaster, master_id):
        raise not_found("Entidad maestra")
    return [
        a.alias
        for a in db.scalars(
            select(EntityAlias).where(EntityAlias.entity_master_id == master_id)
        ).all()
    ]


@router.get("/v1/merge-candidates", response_model=list[MergeCandidateOut], tags=["suppliers"])
@limiter.limit(f"{RATE}/minute")
def list_merge_candidates(
    request: Request,
    db: Session = Depends(get_db),
    status: str = Query("pending"),
    left_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
) -> list[MergeCandidate]:
    stmt = select(MergeCandidate).where(MergeCandidate.status == status)
    if left_type:
        stmt = stmt.where(MergeCandidate.left_type == left_type)
    stmt = stmt.order_by(MergeCandidate.score.desc()).limit(limit)
    return list(db.scalars(stmt).all())
