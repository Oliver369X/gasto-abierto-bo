"""Supplier list/get."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import RATE, get_db, limiter
from api.errors import not_found
from api.schemas import SupplierOut
from schema.models import Supplier

router = APIRouter()


@router.get("/v1/suppliers/{supplier_id}", response_model=SupplierOut, tags=["suppliers"])
@limiter.limit(f"{RATE}/minute")
def get_supplier(request: Request, supplier_id: int, db: Session = Depends(get_db)) -> Supplier:
    row = db.get(Supplier, supplier_id)
    if not row:
        raise not_found("Proveedor")
    return row


@router.get("/v1/suppliers", response_model=list[SupplierOut], tags=["suppliers"])
@limiter.limit(f"{RATE}/minute")
def list_suppliers(
    request: Request,
    db: Session = Depends(get_db),
    q: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[Supplier]:
    stmt = select(Supplier).order_by(Supplier.name)
    if q:
        stmt = stmt.where(Supplier.name.ilike(f"%{q}%"))
    return list(db.scalars(stmt.offset(offset).limit(limit)).all())
