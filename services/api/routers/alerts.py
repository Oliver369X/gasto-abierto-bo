"""Alerts list/get."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import RATE, get_db, limiter
from api.errors import not_found
from api.schemas import AlertOut
from schema.models import Alert

router = APIRouter()


@router.get("/v1/alerts", response_model=list[AlertOut], tags=["alerts"])
@limiter.limit(f"{RATE}/minute")
def list_alerts(
    request: Request,
    db: Session = Depends(get_db),
    severity: Optional[str] = None,
    rule_id: Optional[str] = None,
    entity_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    quality: str = Query("public", pattern="^(public|all)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[Alert]:
    stmt = select(Alert).order_by(Alert.created_at.desc())
    if quality == "public":
        stmt = stmt.where(Alert.is_synthetic.is_(False))
    if severity:
        stmt = stmt.where(Alert.severity == severity)
    if rule_id:
        stmt = stmt.where(Alert.rule_id == rule_id)
    if entity_id is not None:
        stmt = stmt.where(Alert.entity_id == entity_id)
    if supplier_id is not None:
        stmt = stmt.where(Alert.supplier_id == supplier_id)
    return list(db.scalars(stmt.offset(offset).limit(limit)).all())


@router.get("/v1/alerts/{alert_id}", response_model=AlertOut, tags=["alerts"])
@limiter.limit(f"{RATE}/minute")
def get_alert(request: Request, alert_id: int, db: Session = Depends(get_db)) -> Alert:
    row = db.get(Alert, alert_id)
    if not row:
        raise not_found("Alerta")
    return row
