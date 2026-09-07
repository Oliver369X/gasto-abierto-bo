"""Audits and findings."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import RATE, get_db, limiter
from api.schemas import AuditFindingOut, AuditOut
from schema.models import AuditFinding, AuditReport

router = APIRouter()


@router.get("/v1/audits", response_model=list[AuditOut], tags=["audits"])
@limiter.limit(f"{RATE}/minute")
def list_audits(
    request: Request,
    db: Session = Depends(get_db),
    entity_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[AuditReport]:
    stmt = select(AuditReport)
    if entity_id is not None:
        stmt = stmt.where(AuditReport.entity_id == entity_id)
    return list(db.scalars(stmt.offset(offset).limit(limit)).all())


@router.get("/v1/audits/{audit_id}", response_model=AuditOut, tags=["audits"])
@limiter.limit(f"{RATE}/minute")
def get_audit(request: Request, audit_id: int, db: Session = Depends(get_db)) -> AuditReport:
    audit = db.get(AuditReport, audit_id)
    if not audit:
        raise HTTPException(404, "Audit not found")
    return audit


@router.get("/v1/audits/{audit_id}/findings", response_model=list[AuditFindingOut], tags=["audits"])
@limiter.limit(f"{RATE}/minute")
def audit_findings(
    request: Request, audit_id: int, db: Session = Depends(get_db)
) -> list[AuditFinding]:
    if not db.get(AuditReport, audit_id):
        raise HTTPException(404, "Audit not found")
    return list(
        db.scalars(select(AuditFinding).where(AuditFinding.audit_report_id == audit_id)).all()
    )
