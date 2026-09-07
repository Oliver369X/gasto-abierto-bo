"""Meta endpoints: health, stats, search, categories, ingestion-runs, sources."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.deps import RATE, get_db, limiter
from api.schemas import (
    CategoryOut,
    HealthOut,
    IngestionRunOut,
    SearchHit,
    SearchOut,
    SourceOut,
    StatsOut,
)
from common.categorize import CATEGORIES, CATEGORY_LABELS
from common.data_quality import public_contract_filter
from common.http_client import proxy_status
from schema.models import Alert, Contract, Entity, IngestionRun, Supplier

router = APIRouter()


@router.get("/v1/health", response_model=HealthOut, tags=["meta"])
@limiter.limit(f"{RATE}/minute")
def health(request: Request) -> HealthOut:
    return HealthOut(status="ok", proxy=proxy_status())


@router.get("/v1/stats", response_model=StatsOut, tags=["meta"])
@limiter.limit(f"{RATE}/minute")
def stats(
    request: Request,
    db: Session = Depends(get_db),
    quality: str = Query("public", pattern="^(public|all)$"),
) -> StatsOut:
    from decimal import Decimal as _Dec

    from worker.gasto.stats_snapshot import get_or_refresh_stats

    payload = get_or_refresh_stats(db, quality=quality)
    return StatsOut(
        entities=int(payload.get("entities") or 0),
        suppliers=int(payload.get("suppliers") or 0),
        contracts=int(payload.get("contracts") or 0),
        budgets=int(payload.get("budgets") or 0),
        alerts=int(payload.get("alerts") or 0),
        audits=int(payload.get("audits") or 0),
        discrepancies=int(payload.get("discrepancies") or 0),
        documents=int(payload.get("documents") or 0),
        total_contract_amount=_Dec(str(payload.get("total_contract_amount") or 0)),
        alerts_by_severity={
            str(k): int(v) for k, v in (payload.get("alerts_by_severity") or {}).items()
        },
    )


@router.get("/v1/search", response_model=SearchOut, tags=["meta"])
@limiter.limit(f"{RATE}/minute")
def search(
    request: Request,
    db: Session = Depends(get_db),
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=50),
) -> SearchOut:
    like = f"%{q.strip()}%"
    hits: list[SearchHit] = []
    for e in db.scalars(
        select(Entity)
        .where(Entity.name.ilike(like), Entity.is_synthetic.is_(False))
        .limit(limit)
    ).all():
        hits.append(
            SearchHit(
                type="entity",
                id=e.id,
                title=e.name,
                subtitle=e.level,
                href=f"/entidad/{e.id}",
            )
        )
    for c in db.scalars(
        select(Contract)
        .where(
            public_contract_filter(Contract),
            (Contract.cuce.ilike(like)) | (Contract.object_description.ilike(like)),
        )
        .limit(limit)
    ).all():
        hits.append(
            SearchHit(
                type="contract",
                id=c.id,
                title=c.cuce or f"Contrato #{c.id}",
                subtitle=(c.object_description or "")[:120] or c.category,
                href=f"/contrato/{c.id}",
            )
        )
    for s in db.scalars(
        select(Supplier)
        .where(Supplier.name.ilike(like), Supplier.is_synthetic.is_(False))
        .limit(limit)
    ).all():
        hits.append(
            SearchHit(
                type="supplier",
                id=s.id,
                title=s.name,
                subtitle=s.nit,
                href=f"/proveedor/{s.id}",
            )
        )
    for a in db.scalars(
        select(Alert)
        .where(
            Alert.is_synthetic.is_(False),
            Alert.title.ilike(like) | Alert.explanation.ilike(like),
        )
        .limit(limit)
    ).all():
        hits.append(
            SearchHit(
                type="alert",
                id=a.id,
                title=a.title,
                subtitle=a.severity,
                href=f"/alertas/{a.id}",
            )
        )
    return SearchOut(q=q, hits=hits[:limit])


@router.get("/v1/categories", response_model=list[CategoryOut], tags=["meta"])
@limiter.limit(f"{RATE}/minute")
def list_categories(request: Request, db: Session = Depends(get_db)) -> list[CategoryOut]:
    counts = dict(
        db.execute(
            select(Contract.category, func.count(Contract.id))
            .where(
                public_contract_filter(Contract),
                Contract.category.is_not(None),
            )
            .group_by(Contract.category)
        ).all()
    )
    out: list[CategoryOut] = []
    for cid in CATEGORIES:
        out.append(
            CategoryOut(
                id=cid,
                label=CATEGORY_LABELS.get(cid, cid),
                contracts=int(counts.get(cid, 0)),
            )
        )
    return out


@router.get("/v1/ingestion-runs", response_model=list[IngestionRunOut], tags=["meta"])
@limiter.limit(f"{RATE}/minute")
def list_ingestion_runs(
    request: Request,
    db: Session = Depends(get_db),
    source_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
) -> list[IngestionRun]:
    stmt = select(IngestionRun).order_by(IngestionRun.started_at.desc())
    if source_id:
        stmt = stmt.where(IngestionRun.source_id == source_id)
    return list(db.scalars(stmt.limit(limit)).all())


@router.get("/v1/sources", response_model=list[SourceOut], tags=["meta"])
@limiter.limit(f"{RATE}/minute")
def list_sources(request: Request, db: Session = Depends(get_db)) -> list[SourceOut]:
    known = [
        "agetic",
        "sicoes",
        "presupuesto_abierto",
        "cge",
        "gad_scz",
        "gam_scz",
        "mindef",
        "abt",
        "gaceta_scz",
        "sernap",
        "firms",
        "seed",
        "seed_fire",
        "rules",
        "fire_rules",
    ]
    out: list[SourceOut] = []
    for sid in known:
        run = db.scalars(
            select(IngestionRun)
            .where(IngestionRun.source_id == sid)
            .order_by(IngestionRun.started_at.desc())
            .limit(1)
        ).first()
        out.append(
            SourceOut(
                source_id=sid,
                last_status=run.status if run else None,
                last_finished_at=run.finished_at if run else None,
                records_out=run.records_out if run else None,
            )
        )
    return out
