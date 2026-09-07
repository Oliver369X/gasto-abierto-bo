"""AURA Incendios — public read API for the forest-fire spending ledger."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from common.fire.classify import ATTRIBUTION_LABELS, CYCLE_LABELS
from common.fire.coverage import build_ola1_coverage
from common.fire.ledger import amount_by_bucket, amount_for_public_kpi
from common.fire.rollup import build_rollup
from schema.models import (
    ActiveFireDetection,
    DonationAid,
    EmergencyDeclaration,
    Entity,
    FireCapabilityAsset,
    FireCluster,
    FireEvent,
    FireExpenditure,
    FireLink,
    FireSeason,
    OperationalOutput,
    Territory,
)

# Router is mounted with limiter from main; endpoints receive Request for slowapi.


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class FireSeasonOut(ORMModel):
    id: int
    year: int
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    quality_grade: str
    notes: Optional[str] = None


class AttributionBucket(BaseModel):
    attribution: str
    label: str
    count: int
    amount: Decimal


class CycleBucket(BaseModel):
    cycle: str
    label: str
    count: int
    amount: Decimal


class DepartmentBucket(BaseModel):
    slug: str
    name: str
    count: int
    amount_direct: Decimal
    amount_probable: Decimal


class FireLedgerOut(BaseModel):
    year: int
    department: Optional[str] = None
    quality_grade: Optional[str] = None
    disclaimer: str
    expenditures_count: int
    amount_direct_verifiable: Decimal
    amount_probable: Decimal
    amount_parcial: Decimal
    amount_contracted: Decimal
    amount_synthetic_excluded: Decimal = Decimal("0")
    amount_pools_no_relacionado: Decimal = Decimal("0")
    donations_amount: Decimal
    donations_in_kind: int
    by_attribution: list[AttributionBucket]
    by_cycle: list[CycleBucket]
    by_department: list[DepartmentBucket]
    by_ledger_bucket: list[AttributionBucket] = Field(default_factory=list)


class FireExpenditureOut(ORMModel):
    id: int
    code: str
    year: int
    title: str
    object_description: Optional[str] = None
    attribution: str
    confidence_score: Decimal
    classification_method: str
    cycle: str
    amount_contract: Optional[Decimal] = None
    amount_attributed: Optional[Decimal] = None
    amount_total: Optional[Decimal] = None
    amount_attributed_low: Optional[Decimal] = None
    amount_attributed_base: Optional[Decimal] = None
    amount_attributed_high: Optional[Decimal] = None
    allocation_method: Optional[str] = None
    allocation_confidence: Optional[Decimal] = None
    ledger_bucket: Optional[str] = None
    is_synthetic: bool = False
    recovery_status: Optional[str] = None
    link_strength: Optional[str] = None
    currency: str = "BOB"
    quality_grade: str
    cuce: Optional[str] = None
    paying_entity_id: Optional[int] = None
    paying_entity_name: Optional[str] = None
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    beneficiary_territory_id: Optional[int] = None
    beneficiary_territory_name: Optional[str] = None
    beneficiary_territory_slug: Optional[str] = None
    beneficiary_territory_level: Optional[str] = None
    contract_id: Optional[int] = None
    document_id: Optional[int] = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    source_id: str


class OperationalOut(ORMModel):
    id: int
    year: int
    metric_key: str
    metric_label: str
    value_numeric: Optional[Decimal] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    evidence_page: Optional[int] = None
    evidence_quote: Optional[str] = None
    source_id: str
    entity_name: Optional[str] = None


class FireMetricsOut(BaseModel):
    year: int
    preventive_ratio: Optional[Decimal] = None
    reactive_ratio: Optional[Decimal] = None
    top5_supplier_share: Optional[Decimal] = None
    cost_per_operation: Optional[Decimal] = None
    cost_per_fire_attended: Optional[Decimal] = None
    operations_count: Optional[Decimal] = None
    fires_mitigated: Optional[Decimal] = None
    notes: list[str] = Field(default_factory=list)


DISCLAIMER = (
    "Gasto mínimo directamente verificable vs montos probables/parciales. "
    "No existe una cifra oficial consolidada única de «presupuesto para incendios»; "
    "este ledger reconstruye expedientes con evidencia. "
    "El pool emergencia/desastre MINDEF NO se atribuye completo a incendios."
)
GEOJSON_PATH = (
    Path(__file__).resolve().parents[2]
    / "packages" / "common" / "fire" / "geo" / "ola1_departments.geojson"
)


def _dec(v: Any) -> Decimal:
    if v is None:
        return Decimal("0")
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _attr_val(r: FireExpenditure) -> str:
    a = r.attribution
    return a.value if hasattr(a, "value") else str(a)


def _cycle_val(r: FireExpenditure) -> str:
    c = r.cycle
    return c.value if hasattr(c, "value") else str(c)


def _territory_filter_ids(db: Session, territory: str) -> Optional[list[int]]:
    """Resolve a slug/name to territory ids including direct children.

    Returns None when no territory matches (caller should return empty).
    """
    tl = territory.lower().replace(" ", "-")
    match = db.scalars(
        select(Territory).where(
            (Territory.slug == tl) | (func.lower(Territory.name) == territory.lower())
        )
    ).first()
    if not match:
        return None
    child_ids = [
        c.id
        for c in db.scalars(select(Territory).where(Territory.parent_id == match.id)).all()
    ]
    return [match.id, *child_ids]


def _exp_out(row: FireExpenditure) -> FireExpenditureOut:
    return FireExpenditureOut(
        id=row.id,
        code=row.code,
        year=row.year,
        title=row.title,
        object_description=row.object_description,
        attribution=row.attribution.value if hasattr(row.attribution, "value") else str(row.attribution),
        confidence_score=_dec(row.confidence_score),
        classification_method=row.classification_method,
        cycle=row.cycle.value if hasattr(row.cycle, "value") else str(row.cycle),
        amount_contract=row.amount_contract,
        amount_attributed=row.amount_attributed,
        amount_total=getattr(row, "amount_total", None),
        amount_attributed_low=getattr(row, "amount_attributed_low", None),
        amount_attributed_base=getattr(row, "amount_attributed_base", None),
        amount_attributed_high=getattr(row, "amount_attributed_high", None),
        allocation_method=getattr(row, "allocation_method", None),
        allocation_confidence=getattr(row, "allocation_confidence", None),
        ledger_bucket=getattr(row, "ledger_bucket", None),
        is_synthetic=bool(getattr(row, "is_synthetic", False)),
        recovery_status=getattr(row, "recovery_status", None),
        link_strength=getattr(row, "link_strength", None),
        currency=row.currency,
        quality_grade=row.quality_grade,
        cuce=row.cuce,
        paying_entity_id=row.paying_entity_id,
        paying_entity_name=row.paying_entity.name if row.paying_entity else None,
        supplier_id=row.supplier_id,
        supplier_name=row.supplier.name if row.supplier else None,
        beneficiary_territory_id=row.beneficiary_territory_id,
        beneficiary_territory_name=(
            row.beneficiary_territory.name if row.beneficiary_territory else None
        ),
        beneficiary_territory_slug=(
            row.beneficiary_territory.slug if row.beneficiary_territory else None
        ),
        beneficiary_territory_level=(
            (row.beneficiary_territory.level.value if hasattr(row.beneficiary_territory.level, "value") else str(row.beneficiary_territory.level))
            if row.beneficiary_territory
            else None
        ),
        contract_id=row.contract_id,
        document_id=row.document_id,
        evidence=row.evidence or {},
        source_id=row.source_id,
    )


def create_fire_router(get_db, limiter, rate: str) -> APIRouter:
    router = APIRouter(prefix="/v1/fire", tags=["incendios"])

    @router.get("/seasons", response_model=list[FireSeasonOut])
    @limiter.limit(f"{rate}/minute")
    def list_seasons(request: Request, db: Session = Depends(get_db)) -> list[FireSeasonOut]:
        rows = list(db.scalars(select(FireSeason).order_by(FireSeason.year.desc())).all())
        return [
            FireSeasonOut(
                id=r.id,
                year=r.year,
                start_date=r.start_date.isoformat() if r.start_date else None,
                end_date=r.end_date.isoformat() if r.end_date else None,
                quality_grade=r.quality_grade,
                notes=r.notes,
            )
            for r in rows
        ]

    @router.get("/ledger", response_model=FireLedgerOut)
    @limiter.limit(f"{rate}/minute")
    def fire_ledger(
        request: Request,
        db: Session = Depends(get_db),
        year: int = Query(2024),
        department: Optional[str] = Query(None, description="Nombre o slug de departamento"),
    ) -> FireLedgerOut:
        stmt = select(FireExpenditure).options(
            joinedload(FireExpenditure.beneficiary_territory),
            joinedload(FireExpenditure.paying_entity),
            joinedload(FireExpenditure.supplier),
        ).where(FireExpenditure.year == year)
        rows = list(db.scalars(stmt).unique().all())

        if department:
            dep_l = department.lower().replace(" ", "-")
            # Match department itself OR municipalities under it
            parent = next(
                (
                    r.beneficiary_territory
                    for r in rows
                    if r.beneficiary_territory
                    and (
                        r.beneficiary_territory.slug == dep_l
                        or r.beneficiary_territory.name.lower() == department.lower()
                    )
                    and getattr(r.beneficiary_territory.level, "value", r.beneficiary_territory.level)
                    == "departamento"
                ),
                None,
            )
            if not parent:
                parent = db.scalars(
                    select(Territory).where(
                        (Territory.slug == dep_l) | (Territory.name.ilike(department))
                    )
                ).first()
            parent_id = parent.id if parent else None
            child_ids = set()
            if parent_id:
                child_ids = {
                    c.id
                    for c in db.scalars(
                        select(Territory).where(Territory.parent_id == parent_id)
                    ).all()
                }
            rows = [
                r
                for r in rows
                if r.beneficiary_territory
                and (
                    r.beneficiary_territory.slug == dep_l
                    or r.beneficiary_territory.name.lower() == department.lower()
                    or (parent_id and r.beneficiary_territory_id == parent_id)
                    or (r.beneficiary_territory_id in child_ids)
                )
            ]

        season = db.scalars(select(FireSeason).where(FireSeason.year == year)).first()

        by_attr: dict[str, AttributionBucket] = {}
        by_cycle: dict[str, CycleBucket] = {}
        by_dept: dict[str, DepartmentBucket] = {}
        amount_direct = Decimal("0")
        amount_direct_verifiable = Decimal("0")
        amount_probable = Decimal("0")
        amount_parcial = Decimal("0")
        amount_contracted = Decimal("0")
        amount_synthetic_excluded = Decimal("0")
        amount_pools = Decimal("0")
        by_bucket: dict[str, AttributionBucket] = {}

        # Cache parent departments for municipalities
        parent_cache: dict[int, Territory] = {}

        def _dept_for(terr: Territory | None) -> Territory | None:
            if not terr:
                return None
            lvl = getattr(terr.level, "value", terr.level)
            if lvl == "departamento":
                return terr
            if lvl == "municipio" and terr.parent_id:
                if terr.parent_id not in parent_cache:
                    p = db.get(Territory, terr.parent_id)
                    if p:
                        parent_cache[terr.parent_id] = p
                return parent_cache.get(terr.parent_id)
            return None

        for r in rows:
            attr = _attr_val(r)
            cyc = _cycle_val(r)
            amt = _dec(r.amount_attributed)
            amount_contracted += _dec(r.amount_contract)
            bucket, bucket_amt = amount_by_bucket(r)
            if bucket not in by_bucket:
                by_bucket[bucket] = AttributionBucket(
                    attribution=bucket,
                    label=bucket.replace("_", " ").title(),
                    count=0,
                    amount=Decimal("0"),
                )
            by_bucket[bucket].count += 1
            by_bucket[bucket].amount += bucket_amt

            if getattr(r, "is_synthetic", False) or bucket == "sintetico":
                amount_synthetic_excluded += _dec(r.amount_contract)
            if bucket == "no_relacionado":
                amount_pools += _dec(r.amount_contract)

            if attr not in by_attr:
                by_attr[attr] = AttributionBucket(
                    attribution=attr,
                    label=ATTRIBUTION_LABELS.get(attr, attr),
                    count=0,
                    amount=Decimal("0"),
                )
            by_attr[attr].count += 1
            # Only non-synthetic attributed amounts in attribution rollup for honesty
            if not getattr(r, "is_synthetic", False):
                by_attr[attr].amount += amt

            if cyc not in by_cycle:
                by_cycle[cyc] = CycleBucket(
                    cycle=cyc,
                    label=CYCLE_LABELS.get(cyc, cyc),
                    count=0,
                    amount=Decimal("0"),
                )
            by_cycle[cyc].count += 1
            if not getattr(r, "is_synthetic", False):
                by_cycle[cyc].amount += amt

            if attr == "directo" and not getattr(r, "is_synthetic", False):
                amount_direct += amt
            amount_direct_verifiable += amount_for_public_kpi(r)
            if attr == "probable" and not getattr(r, "is_synthetic", False):
                amount_probable += amt
            elif attr == "parcial" and not getattr(r, "is_synthetic", False):
                amount_parcial += amt

            dept = _dept_for(r.beneficiary_territory)
            if dept and not getattr(r, "is_synthetic", False):
                slug = dept.slug
                if slug not in by_dept:
                    by_dept[slug] = DepartmentBucket(
                        slug=slug,
                        name=dept.name,
                        count=0,
                        amount_direct=Decimal("0"),
                        amount_probable=Decimal("0"),
                    )
                by_dept[slug].count += 1
                if attr == "directo":
                    by_dept[slug].amount_direct += amt
                elif attr == "probable":
                    by_dept[slug].amount_probable += amt

        donations = list(
            db.scalars(select(DonationAid).where(DonationAid.year == year)).all()
        )
        don_amt = sum((_dec(d.amount) for d in donations), Decimal("0"))
        don_kind = sum(1 for d in donations if d.in_kind)

        return FireLedgerOut(
            year=year,
            department=department,
            quality_grade=season.quality_grade if season else None,
            disclaimer=DISCLAIMER,
            expenditures_count=len(rows),
            amount_direct_verifiable=amount_direct_verifiable,
            amount_probable=amount_probable,
            amount_parcial=amount_parcial,
            amount_contracted=amount_contracted,
            amount_synthetic_excluded=amount_synthetic_excluded,
            amount_pools_no_relacionado=amount_pools,
            donations_amount=don_amt,
            donations_in_kind=don_kind,
            by_attribution=sorted(by_attr.values(), key=lambda x: x.attribution),
            by_cycle=sorted(by_cycle.values(), key=lambda x: x.cycle),
            by_department=sorted(by_dept.values(), key=lambda x: x.name),
            by_ledger_bucket=sorted(by_bucket.values(), key=lambda x: x.attribution),
        )

    @router.get("/expenditures", response_model=list[FireExpenditureOut])
    @limiter.limit(f"{rate}/minute")
    def list_expenditures(
        request: Request,
        db: Session = Depends(get_db),
        year: Optional[int] = None,
        attribution: Optional[str] = None,
        cycle: Optional[str] = None,
        entity_id: Optional[int] = None,
        territory: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ) -> list[FireExpenditureOut]:
        stmt = (
            select(FireExpenditure)
            .options(
                joinedload(FireExpenditure.beneficiary_territory),
                joinedload(FireExpenditure.paying_entity),
                joinedload(FireExpenditure.supplier),
            )
            .order_by(FireExpenditure.code)
        )
        if year is not None:
            stmt = stmt.where(FireExpenditure.year == year)
        if attribution:
            stmt = stmt.where(FireExpenditure.attribution == attribution)
        if cycle:
            stmt = stmt.where(FireExpenditure.cycle == cycle)
        if entity_id is not None:
            stmt = stmt.where(FireExpenditure.paying_entity_id == entity_id)
        if territory:
            ids = _territory_filter_ids(db, territory)
            if ids is None:
                return []
            stmt = stmt.where(FireExpenditure.beneficiary_territory_id.in_(ids))
        rows = list(db.scalars(stmt.offset(offset).limit(limit * 3)).unique().all())
        if q:
            ql = q.lower()
            rows = [
                r
                for r in rows
                if ql in (r.title or "").lower()
                or ql in (r.object_description or "").lower()
                or ql in (r.cuce or "").lower()
                or ql in (r.code or "").lower()
            ]
        return [_exp_out(r) for r in rows[:limit]]

    @router.get("/expenditures/{expenditure_id}", response_model=FireExpenditureOut)
    @limiter.limit(f"{rate}/minute")
    def get_expenditure(
        request: Request,
        expenditure_id: int,
        db: Session = Depends(get_db),
    ) -> FireExpenditureOut:
        row = db.scalars(
            select(FireExpenditure)
            .options(
                joinedload(FireExpenditure.beneficiary_territory),
                joinedload(FireExpenditure.paying_entity),
                joinedload(FireExpenditure.supplier),
            )
            .where(FireExpenditure.id == expenditure_id)
        ).unique().first()
        if not row:
            # try by code
            row = db.scalars(
                select(FireExpenditure)
                .options(
                    joinedload(FireExpenditure.beneficiary_territory),
                    joinedload(FireExpenditure.paying_entity),
                    joinedload(FireExpenditure.supplier),
                )
                .where(FireExpenditure.code == str(expenditure_id))
            ).unique().first()
        if not row:
            raise HTTPException(404, "Expediente no encontrado")
        return _exp_out(row)

    @router.get("/expenditures/by-code/{code}", response_model=FireExpenditureOut)
    @limiter.limit(f"{rate}/minute")
    def get_expenditure_by_code(
        request: Request,
        code: str,
        db: Session = Depends(get_db),
    ) -> FireExpenditureOut:
        row = db.scalars(
            select(FireExpenditure)
            .options(
                joinedload(FireExpenditure.beneficiary_territory),
                joinedload(FireExpenditure.paying_entity),
                joinedload(FireExpenditure.supplier),
            )
            .where(FireExpenditure.code == code)
        ).unique().first()
        if not row:
            raise HTTPException(404, "Expediente no encontrado")
        return _exp_out(row)

    @router.get("/operations", response_model=list[OperationalOut])
    @limiter.limit(f"{rate}/minute")
    def list_operations(
        request: Request,
        db: Session = Depends(get_db),
        year: int = Query(2024),
    ) -> list[OperationalOut]:
        rows = list(
            db.scalars(
                select(OperationalOutput)
                .where(OperationalOutput.year == year)
                .order_by(OperationalOutput.metric_key)
            ).all()
        )
        out: list[OperationalOut] = []
        for r in rows:
            ent = db.get(Entity, r.entity_id) if r.entity_id else None
            out.append(
                OperationalOut(
                    id=r.id,
                    year=r.year,
                    metric_key=r.metric_key,
                    metric_label=r.metric_label,
                    value_numeric=r.value_numeric,
                    value_text=r.value_text,
                    unit=r.unit,
                    evidence_page=r.evidence_page,
                    evidence_quote=r.evidence_quote,
                    source_id=r.source_id,
                    entity_name=ent.name if ent else None,
                )
            )
        return out

    @router.get("/metrics", response_model=FireMetricsOut)
    @limiter.limit(f"{rate}/minute")
    def fire_metrics(
        request: Request,
        db: Session = Depends(get_db),
        year: int = Query(2024),
    ) -> FireMetricsOut:
        rows = list(
            db.scalars(select(FireExpenditure).where(FireExpenditure.year == year)).all()
        )
        total = sum(
            (_dec(r.amount_attributed) for r in rows if _attr_val(r) in ("directo", "probable", "parcial")),
            Decimal("0"),
        )
        prev = sum(
            (_dec(r.amount_attributed) for r in rows if _cycle_val(r) == "prevencion"),
            Decimal("0"),
        )
        resp = sum(
            (_dec(r.amount_attributed) for r in rows if _cycle_val(r) == "respuesta"),
            Decimal("0"),
        )
        notes = [
            "Ratios solo usan montos atribuidos del ledger (no el pool emergencia/desastre completo).",
            "Coste por operación/incendio requiere alineación numerador-denominador; se calcula solo con gasto de respuesta directo.",
        ]
        preventive_ratio = (prev / total) if total else None
        reactive_ratio = (resp / total) if total else None

        # Top 5 suppliers share of attributed amount
        by_sup: dict[int, Decimal] = {}
        for r in rows:
            if not r.supplier_id:
                continue
            by_sup[r.supplier_id] = by_sup.get(r.supplier_id, Decimal("0")) + _dec(
                r.amount_attributed
            )
        top5 = sum(sorted(by_sup.values(), reverse=True)[:5], Decimal("0"))
        all_sup = sum(by_sup.values(), Decimal("0"))
        top5_share = (top5 / all_sup) if all_sup else None

        ops = db.scalars(
            select(OperationalOutput).where(
                OperationalOutput.year == year,
                OperationalOutput.metric_key == "operaciones",
            )
        ).first()
        fires = db.scalars(
            select(OperationalOutput).where(
                OperationalOutput.year == year,
                OperationalOutput.metric_key == "incendios_mitigados",
            )
        ).first()
        direct_resp = sum(
            (
                _dec(r.amount_attributed)
                for r in rows
                if _attr_val(r) == "directo" and _cycle_val(r) == "respuesta"
            ),
            Decimal("0"),
        )
        cost_op = None
        cost_fire = None
        if ops and ops.value_numeric and ops.value_numeric > 0 and direct_resp:
            cost_op = (direct_resp / _dec(ops.value_numeric)).quantize(Decimal("0.01"))
        if fires and fires.value_numeric and fires.value_numeric > 0 and direct_resp:
            cost_fire = (direct_resp / _dec(fires.value_numeric)).quantize(Decimal("0.01"))

        return FireMetricsOut(
            year=year,
            preventive_ratio=preventive_ratio.quantize(Decimal("0.0001")) if preventive_ratio is not None else None,
            reactive_ratio=reactive_ratio.quantize(Decimal("0.0001")) if reactive_ratio is not None else None,
            top5_supplier_share=top5_share.quantize(Decimal("0.0001")) if top5_share is not None else None,
            cost_per_operation=cost_op,
            cost_per_fire_attended=cost_fire,
            operations_count=ops.value_numeric if ops else None,
            fires_mitigated=fires.value_numeric if fires else None,
            notes=notes,
        )

    @router.get("/history")
    @limiter.limit(f"{rate}/minute")
    def fire_history(request: Request, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
        seasons = list(db.scalars(select(FireSeason).order_by(FireSeason.year)).all())
        out: list[dict[str, Any]] = []
        for s in seasons:
            rows = list(
                db.scalars(select(FireExpenditure).where(FireExpenditure.year == s.year)).all()
            )
            direct = sum(
                (_dec(r.amount_attributed) for r in rows if _attr_val(r) == "directo"),
                Decimal("0"),
            )
            probable = sum(
                (_dec(r.amount_attributed) for r in rows if _attr_val(r) == "probable"),
                Decimal("0"),
            )
            hotspots = db.scalar(
                select(func.count())
                .select_from(ActiveFireDetection)
                .where(ActiveFireDetection.year == s.year)
            ) or 0
            ha_row = db.scalars(
                select(OperationalOutput).where(
                    OperationalOutput.year == s.year,
                    OperationalOutput.metric_key == "hectareas_quemadas_dgf_simb",
                )
            ).first()
            out.append(
                {
                    "year": s.year,
                    "quality_grade": s.quality_grade,
                    "notes": s.notes,
                    "expenditures": len(rows),
                    "amount_direct": direct,
                    "amount_direct_verifiable": sum(
                        (
                            _dec(r.amount_attributed)
                            for r in rows
                            if _attr_val(r) == "directo"
                            and (r.quality_grade or "").upper() == "A"
                            and not (r.evidence or {}).get("is_synthetic")
                        ),
                        Decimal("0"),
                    ),
                    "amount_probable": probable,
                    "firms_detections": int(hotspots),
                    "hectares_dgf_simb": float(ha_row.value_numeric)
                    if ha_row and ha_row.value_numeric is not None
                    else None,
                }
            )
        return out

    @router.get("/declarations")
    @limiter.limit(f"{rate}/minute")
    def list_declarations(
        request: Request,
        db: Session = Depends(get_db),
        year: Optional[int] = None,
        event_type: Optional[str] = None,
        limit: int = Query(50, ge=1, le=200),
    ) -> list[dict[str, Any]]:
        rows = list(
            db.scalars(select(EmergencyDeclaration).order_by(EmergencyDeclaration.id.desc())).all()
        )
        out: list[dict[str, Any]] = []
        for r in rows:
            if event_type and r.event_type != event_type:
                continue
            if year and r.promulgated_at and r.promulgated_at.year != year:
                continue
            if year and not r.promulgated_at:
                continue
            out.append(
                {
                    "id": r.id,
                    "title": r.title,
                    "decree_number": r.decree_number,
                    "event_type": r.event_type,
                    "promulgated_at": r.promulgated_at.isoformat() if r.promulgated_at else None,
                    "published_at": r.published_at.isoformat() if r.published_at else None,
                    "url": r.url,
                    "summary": r.summary,
                    "source_id": r.source_id,
                }
            )
            if len(out) >= limit:
                break
        return out

    @router.get("/satellite")
    @limiter.limit(f"{rate}/minute")
    def satellite_summary(
        request: Request,
        db: Session = Depends(get_db),
        year: int = Query(2024),
        limit: int = Query(100, ge=1, le=500),
    ) -> dict[str, Any]:
        rows = list(
            db.scalars(
                select(ActiveFireDetection)
                .where(ActiveFireDetection.year == year)
                .order_by(ActiveFireDetection.id.desc())
                .limit(limit)
            ).all()
        )
        by_dept: dict[str, int] = {}
        for r in rows:
            d = r.department or "Sin departamento"
            by_dept[d] = by_dept.get(d, 0) + 1
        total = db.scalar(
            select(func.count())
            .select_from(ActiveFireDetection)
            .where(ActiveFireDetection.year == year)
        ) or 0
        return {
            "year": year,
            "total_detections": int(total),
            "disclaimer": (
                "Un foco de calor no equivale a una hectárea quemada. "
                "Capa de resultados espaciales, no de gasto."
            ),
            "by_department": [
                {"department": k, "count": v} for k, v in sorted(by_dept.items(), key=lambda x: -x[1])
            ],
            "sample": [
                {
                    "id": r.id,
                    "acq_date": r.acq_date.isoformat() if r.acq_date else None,
                    "latitude": r.latitude,
                    "longitude": r.longitude,
                    "department": r.department,
                    "municipality": r.municipality,
                    "satellite": r.satellite,
                    "confidence": r.confidence,
                    "frp": r.frp,
                }
                for r in rows[:50]
            ],
        }

    @router.get("/compare")
    @limiter.limit(f"{rate}/minute")
    def fire_compare(
        request: Request,
        db: Session = Depends(get_db),
        year: int = Query(2024),
    ) -> dict[str, Any]:
        """Anunciado / pool emergencia vs gasto verificable en incendios."""
        from schema.models import Discrepancy

        rows = list(
            db.scalars(select(FireExpenditure).where(FireExpenditure.year == year)).all()
        )
        direct_all = sum(
            (_dec(r.amount_attributed) for r in rows if _attr_val(r) == "directo"),
            Decimal("0"),
        )
        direct = sum(
            (
                _dec(r.amount_attributed)
                for r in rows
                if _attr_val(r) == "directo"
                and (r.quality_grade or "").upper() == "A"
                and not (r.evidence or {}).get("is_synthetic")
            ),
            Decimal("0"),
        )
        probable = sum((_dec(r.amount_attributed) for r in rows if _attr_val(r) == "probable"), Decimal("0"))
        # Pool multi-evento documentado en RPC: humanitaria+sequía+caminera+rehab+donaciones vecinos
        pool_from_real = sum(
            (
                _dec(r.amount_contract)
                for r in rows
                if (r.code or "").startswith("FIRE-BO-2024-REAL-")
                and _attr_val(r) in ("no_relacionado", "parcial")
            ),
            Decimal("0"),
        )
        pool = db.scalars(
            select(OperationalOutput).where(
                OperationalOutput.year == year,
                OperationalOutput.metric_key == "monto_emergencia_desastre_ejecutado",
            )
        ).first()
        disc = db.scalars(
            select(Discrepancy)
            .where(Discrepancy.concept == f"fire:emergencia_pool_vs_atribuible:{year}")
            .limit(1)
        ).first()
        if not disc:
            disc = db.scalars(
                select(Discrepancy).where(Discrepancy.concept.like(f"fire:%:{year}"))
            ).first()
        pool_amt = pool_from_real if pool_from_real > 0 else (_dec(pool.value_numeric) if pool else None)
        return {
            "year": year,
            "emergency_disaster_pool_executed": pool_amt,
            "fire_direct_verifiable": direct,
            "fire_direct_all_attributed": direct_all,
            "fire_probable": probable,
            "gap_pool_minus_direct": (pool_amt - direct) if pool_amt is not None else None,
            "disclaimer": (
                "El pool emergencia/desastre MINDEF incluye inundaciones, sequía y otros. "
                "No es el gasto en incendios. El gap no es 'corrupción' automática: es "
                "gasto de otros eventos + gasto de incendios aún no trazado."
            ),
            "discrepancy": {
                "concept": disc.concept,
                "amount_a": disc.amount_a,
                "amount_b": disc.amount_b,
                "source_a": disc.source_a,
                "source_b": disc.source_b,
            }
            if disc
            else None,
        }

    @router.get("/donations")
    @limiter.limit(f"{rate}/minute")
    def list_donations(
        request: Request,
        db: Session = Depends(get_db),
        year: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        stmt = select(DonationAid).order_by(DonationAid.year.desc())
        if year is not None:
            stmt = stmt.where(DonationAid.year == year)
        rows = list(db.scalars(stmt).all())
        return [
            {
                "id": r.id,
                "year": r.year,
                "donor_name": r.donor_name,
                "description": r.description,
                "amount": r.amount,
                "in_kind": r.in_kind,
                "evidence": r.evidence or {},
                "source_id": r.source_id,
            }
            for r in rows
        ]

    @router.get("/territories")
    @limiter.limit(f"{rate}/minute")
    def list_territories(
        request: Request,
        db: Session = Depends(get_db),
        level: Optional[str] = Query(None, description="pais|departamento|municipio"),
        parent_slug: Optional[str] = None,
        year: Optional[int] = Query(None, description="Si se pasa, agrega montos del ledger"),
    ) -> list[dict[str, Any]]:
        stmt = select(Territory).order_by(Territory.name)
        if level:
            stmt = stmt.where(Territory.level == level)
        rows = list(db.scalars(stmt).all())
        parent_id = None
        if parent_slug:
            parent = db.scalars(select(Territory).where(Territory.slug == parent_slug)).first()
            parent_id = parent.id if parent else -1
            rows = [t for t in rows if t.parent_id == parent_id]

        slug_by_id = {
            t.id: t.slug for t in db.scalars(select(Territory)).all()
        }
        out: list[dict[str, Any]] = []
        for t in rows:
            lvl = t.level.value if hasattr(t.level, "value") else str(t.level)
            item: dict[str, Any] = {
                "id": t.id,
                "name": t.name,
                "slug": t.slug,
                "level": lvl,
                "parent_id": t.parent_id,
                "parent_slug": slug_by_id.get(t.parent_id) if t.parent_id else None,
            }
            if year is not None:
                exps = list(
                    db.scalars(
                        select(FireExpenditure).where(
                            FireExpenditure.year == year,
                            FireExpenditure.beneficiary_territory_id == t.id,
                        )
                    ).all()
                )
                # Also roll up children for departments
                if lvl == "departamento":
                    child_ids = [
                        c.id
                        for c in db.scalars(
                            select(Territory).where(Territory.parent_id == t.id)
                        ).all()
                    ]
                    if child_ids:
                        exps += list(
                            db.scalars(
                                select(FireExpenditure).where(
                                    FireExpenditure.year == year,
                                    FireExpenditure.beneficiary_territory_id.in_(child_ids),
                                )
                            ).all()
                        )
                direct = sum(
                    (_dec(e.amount_attributed) for e in exps if _attr_val(e) == "directo"),
                    Decimal("0"),
                )
                probable = sum(
                    (_dec(e.amount_attributed) for e in exps if _attr_val(e) == "probable"),
                    Decimal("0"),
                )
                item["expenditures"] = len(exps)
                item["amount_direct"] = direct
                item["amount_probable"] = probable
                hotspots = db.scalar(
                    select(func.count())
                    .select_from(ActiveFireDetection)
                    .where(
                        ActiveFireDetection.year == year,
                        ActiveFireDetection.department == t.name,
                    )
                ) or 0
                item["firms_detections"] = int(hotspots)
            out.append(item)
        return out

    @router.get("/declarations/{declaration_id}")
    @limiter.limit(f"{rate}/minute")
    def declaration_detail(
        request: Request,
        declaration_id: int,
        db: Session = Depends(get_db),
        window_days: int = Query(90, ge=7, le=365),
    ) -> dict[str, Any]:
        """Declaratoria + expedientes del mismo territorio en ventana temporal."""
        from datetime import timedelta

        decl = db.get(EmergencyDeclaration, declaration_id)
        if not decl:
            raise HTTPException(404, "Declaratoria no encontrada")
        related: list[dict[str, Any]] = []
        if decl.promulgated_at and decl.territory_id:
            start = decl.promulgated_at
            end = start + timedelta(days=window_days)
            # Match territory or its parent department expenditures by year
            terr = db.get(Territory, decl.territory_id)
            terr_ids = [decl.territory_id]
            if terr and terr.parent_id:
                terr_ids.append(terr.parent_id)
            children = list(
                db.scalars(select(Territory).where(Territory.parent_id == decl.territory_id)).all()
            )
            terr_ids.extend(c.id for c in children)
            year = start.year
            exps = list(
                db.scalars(
                    select(FireExpenditure)
                    .options(joinedload(FireExpenditure.beneficiary_territory))
                    .where(
                        FireExpenditure.year == year,
                        FireExpenditure.beneficiary_territory_id.in_(terr_ids),
                    )
                ).unique().all()
            )
            for e in exps:
                related.append(
                    {
                        "id": e.id,
                        "code": e.code,
                        "title": e.title,
                        "attribution": _attr_val(e),
                        "cycle": _cycle_val(e),
                        "amount_attributed": e.amount_attributed,
                        "window": f"{start.isoformat()} → {end.isoformat()}",
                        "note": "Relación por territorio+año (no prueba causalidad)",
                    }
                )
        return {
            "id": decl.id,
            "title": decl.title,
            "decree_number": decl.decree_number,
            "event_type": decl.event_type,
            "promulgated_at": decl.promulgated_at.isoformat() if decl.promulgated_at else None,
            "summary": decl.summary,
            "url": decl.url,
            "related_expenditures": related,
            "related_count": len(related),
        }

    @router.get("/export.csv")
    @limiter.limit(f"{rate}/minute")
    def export_csv(
        request: Request,
        db: Session = Depends(get_db),
        year: Optional[int] = None,
        attribution: Optional[str] = None,
        territory: Optional[str] = None,
    ):
        import csv
        import io

        from fastapi.responses import StreamingResponse

        stmt = (
            select(FireExpenditure)
            .options(
                joinedload(FireExpenditure.beneficiary_territory),
                joinedload(FireExpenditure.paying_entity),
                joinedload(FireExpenditure.supplier),
            )
            .order_by(FireExpenditure.code)
        )
        if year is not None:
            stmt = stmt.where(FireExpenditure.year == year)
        if attribution:
            stmt = stmt.where(FireExpenditure.attribution == attribution)
        if territory:
            ids = _territory_filter_ids(db, territory)
            if ids is None:
                raise HTTPException(404, "Territory not found")
            stmt = stmt.where(FireExpenditure.beneficiary_territory_id.in_(ids))
        rows = list(db.scalars(stmt).unique().all())

        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(
            [
                "code",
                "year",
                "title",
                "attribution",
                "cycle",
                "amount_attributed",
                "amount_contract",
                "quality_grade",
                "cuce",
                "paying_entity",
                "territory",
                "supplier",
                "source_id",
            ]
        )
        for r in rows:
            w.writerow(
                [
                    r.code,
                    r.year,
                    r.title,
                    _attr_val(r),
                    _cycle_val(r),
                    r.amount_attributed,
                    r.amount_contract,
                    r.quality_grade,
                    r.cuce or "",
                    r.paying_entity.name if r.paying_entity else "",
                    r.beneficiary_territory.name if r.beneficiary_territory else "",
                    r.supplier.name if r.supplier else "",
                    r.source_id,
                ]
            )
        buf.seek(0)
        filename = f"aura_incendios_{year or 'all'}.csv"
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @router.get("/suppliers")
    @limiter.limit(f"{rate}/minute")
    def fire_suppliers(
        request: Request,
        db: Session = Depends(get_db),
        year: int = Query(2024),
    ) -> list[dict[str, Any]]:
        rows = list(
            db.scalars(
                select(FireExpenditure)
                .options(joinedload(FireExpenditure.supplier))
                .where(FireExpenditure.year == year)
            ).unique().all()
        )
        agg: dict[int, dict[str, Any]] = {}
        for r in rows:
            if not r.supplier_id:
                continue
            if r.supplier_id not in agg:
                agg[r.supplier_id] = {
                    "supplier_id": r.supplier_id,
                    "name": r.supplier.name if r.supplier else f"#{r.supplier_id}",
                    "count": 0,
                    "amount": Decimal("0"),
                }
            agg[r.supplier_id]["count"] += 1
            agg[r.supplier_id]["amount"] += _dec(r.amount_attributed)
        return sorted(agg.values(), key=lambda x: x["amount"], reverse=True)

    @router.get("/coverage")
    @limiter.limit(f"{rate}/minute")
    def fire_coverage(request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
        """F14/F5: coverage metrics across years and sources."""
        seasons = list(db.scalars(select(FireSeason).order_by(FireSeason.year)).all())
        exps = list(db.scalars(select(FireExpenditure)).all())
        ops = list(db.scalars(select(OperationalOutput)).all())
        by_year: list[dict[str, Any]] = []
        for s in seasons:
            yr = [e for e in exps if e.year == s.year]
            ver = sum(amount_for_public_kpi(e) for e in yr)
            syn = sum(1 for e in yr if getattr(e, "is_synthetic", False))
            ha = next(
                (
                    float(o.value_numeric)
                    for o in ops
                    if o.year == s.year and o.metric_key == "hectareas_quemadas_dgf_simb" and o.value_numeric
                ),
                None,
            )
            by_year.append(
                {
                    "year": s.year,
                    "expenditures": len(yr),
                    "synthetic": syn,
                    "amount_direct_verifiable": ver,
                    "hectares_dgf_simb": ha,
                    "quality_grade": s.quality_grade,
                }
            )
        sources = {}
        for e in exps:
            if getattr(e, "is_synthetic", False):
                continue
            sources[e.source_id] = sources.get(e.source_id, 0) + 1
        events = db.scalar(select(func.count()).select_from(FireEvent)) or 0
        clusters = db.scalar(select(func.count()).select_from(FireCluster)) or 0
        assets = db.scalar(select(func.count()).select_from(FireCapabilityAsset)) or 0
        links = db.scalar(select(func.count()).select_from(FireLink)) or 0
        # Territorial coverage ola 1
        territory_cov = []
        for slug, name in (
            ("santa-cruz", "Santa Cruz"),
            ("beni", "Beni"),
            ("pando", "Pando"),
        ):
            t = db.scalars(select(Territory).where(Territory.slug == slug)).first()
            if not t:
                territory_cov.append({"slug": slug, "name": name, "level": "Sin datos", "count": 0})
                continue
            n = sum(
                1
                for e in exps
                if e.beneficiary_territory_id == t.id and not getattr(e, "is_synthetic", False)
            )
            level = "Alta" if n >= 10 else "Media" if n >= 3 else "Baja" if n >= 1 else "Sin datos"
            territory_cov.append({"slug": slug, "name": name, "level": level, "expenditures": n})
        return {
            "disclaimer": "No constituye el gasto total nacional en incendios.",
            "by_year": by_year,
            "expenditures_by_source": sources,
            "territorial_coverage_ola1": territory_cov,
            "fire_events": int(events),
            "fire_clusters": int(clusters),
            "capability_assets": int(assets),
            "fire_links": int(links),
            "pdf_corpus_catalog": "data/extracted/corpus_v1/manifest.json",
        }

    @router.get("/coverage.geojson")
    @limiter.limit(f"{rate}/minute")
    def fire_coverage_geojson(
        request: Request,
        db: Session = Depends(get_db),
        year: int = Query(2024),
    ) -> dict[str, Any]:
        template = json.loads(GEOJSON_PATH.read_text(encoding="utf-8"))
        expenditures = list(db.scalars(
            select(FireExpenditure).where(FireExpenditure.year == year)
        ).all())
        slugs = [feature["properties"]["slug"] for feature in template["features"]]
        territories = {
            row.slug: row for row in db.scalars(
                select(Territory).where(Territory.slug.in_(slugs))
            ).all()
        }
        coverage = {
            item["slug"]: item
            for item in build_ola1_coverage(
                expenditures,
                territories_by_slug=territories,
            )
        }
        for feature in template["features"]:
            item = coverage[feature["properties"]["slug"]]
            feature["properties"].update({
                "year": year,
                "name": item["name"],
                "slug": item["slug"],
                "level": item["level"],
                "coverage_level": item["level"],
                "expenditures": item["expenditures"],
                "amount_direct_verifiable": item.get("amount_direct_verifiable", 0.0),
            })
        return template

    @router.get("/cycles")
    @limiter.limit(f"{rate}/minute")
    def fire_cycles(
        request: Request,
        db: Session = Depends(get_db),
        year: Optional[int] = None,
    ) -> dict[str, Any]:
        """F6: prevention vs response rollup without double-counting CUCE."""
        rows = list(db.scalars(select(FireExpenditure)).all())
        if year is not None:
            rows = [r for r in rows if r.year == year]
        rollup = build_rollup(rows, [])
        return {
            "disclaimer": "Pagos verificables: not_published. No es gasto total nacional.",
            "years": rollup,
        }

    @router.get("/payers")
    @limiter.limit(f"{rate}/minute")
    def fire_payers(
        request: Request,
        db: Session = Depends(get_db),
        year: int = Query(2024),
        limit: int = Query(15, ge=1, le=50),
    ) -> list[dict[str, Any]]:
        rows = list(
            db.scalars(
                select(FireExpenditure)
                .options(joinedload(FireExpenditure.paying_entity))
                .where(FireExpenditure.year == year)
            ).unique().all()
        )
        agg: dict[int, dict[str, Any]] = {}
        for r in rows:
            if getattr(r, "is_synthetic", False) or not r.paying_entity_id:
                continue
            if r.paying_entity_id not in agg:
                agg[r.paying_entity_id] = {
                    "entity_id": r.paying_entity_id,
                    "name": r.paying_entity.name if r.paying_entity else f"#{r.paying_entity_id}",
                    "count": 0,
                    "amount_probable": Decimal("0"),
                    "amount_verifiable": Decimal("0"),
                }
            agg[r.paying_entity_id]["count"] += 1
            agg[r.paying_entity_id]["amount_verifiable"] += amount_for_public_kpi(r)
            if getattr(r, "ledger_bucket", None) == "probable" and r.amount_attributed:
                agg[r.paying_entity_id]["amount_probable"] += _dec(r.amount_attributed)
        return sorted(agg.values(), key=lambda x: x["count"], reverse=True)[:limit]

    @router.get("/expenditures/{expenditure_id}/chain")
    @limiter.limit(f"{rate}/minute")
    def expenditure_chain(
        request: Request,
        expenditure_id: int,
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        """F12/F14: money→ops→event chain with strength labels."""
        row = db.get(FireExpenditure, expenditure_id)
        if not row:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        links = list(
            db.scalars(
                select(FireLink).where(
                    FireLink.from_type == "fire_expenditure",
                    FireLink.from_id == expenditure_id,
                )
            ).all()
        )
        chain = []
        for link in links:
            item: dict[str, Any] = {
                "strength": link.strength,
                "to_type": link.to_type,
                "to_id": link.to_id,
                "note": link.note,
                "evidence": link.evidence or {},
            }
            if link.to_type == "operational_output":
                op = db.get(OperationalOutput, link.to_id)
                if op:
                    item["label"] = op.metric_label
                    item["metric_key"] = op.metric_key
            elif link.to_type == "fire_event":
                ev = db.get(FireEvent, link.to_id)
                if ev:
                    item["label"] = ev.name
                    item["code"] = ev.code
            chain.append(item)
        return {
            "expenditure_id": row.id,
            "code": row.code,
            "link_strength": row.link_strength,
            "chain": chain,
            "disclaimer": "Vínculos no inventan montos causales ni hectáreas atribuidas al contrato.",
        }

    @router.get("/events")
    @limiter.limit(f"{rate}/minute")
    def list_fire_events(
        request: Request,
        db: Session = Depends(get_db),
        year: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        stmt = select(FireEvent).options(joinedload(FireEvent.territory)).order_by(FireEvent.id)
        rows = list(db.scalars(stmt).unique().all())
        if year is not None:
            seasons = {
                s.id: s.year for s in db.scalars(select(FireSeason)).all()
            }
            rows = [r for r in rows if seasons.get(r.season_id) == year]
        return [
            {
                "id": r.id,
                "code": r.code,
                "name": r.name,
                "start_date": r.start_date.isoformat() if r.start_date else None,
                "end_date": r.end_date.isoformat() if r.end_date else None,
                "confidence": r.confidence,
                "hectares_reported": r.hectares_reported,
                "sources": r.sources or [],
                "territory": r.territory.name if r.territory else None,
            }
            for r in rows
        ]

    @router.get("/capabilities")
    @limiter.limit(f"{rate}/minute")
    def list_capabilities(
        request: Request,
        db: Session = Depends(get_db),
        year: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        stmt = select(FireCapabilityAsset).order_by(FireCapabilityAsset.year, FireCapabilityAsset.asset_type)
        if year is not None:
            stmt = stmt.where(FireCapabilityAsset.year == year)
        rows = list(db.scalars(stmt).all())
        return [
            {
                "id": r.id,
                "year": r.year,
                "asset_type": r.asset_type,
                "name": r.name,
                "ownership": r.ownership,
                "quantity": r.quantity,
                "is_preventive": r.is_preventive,
                "acquired_via": r.acquired_via,
                "source_id": r.source_id,
            }
            for r in rows
        ]

    @router.get("/capabilities/summary")
    @limiter.limit(f"{rate}/minute")
    def capabilities_summary(
        request: Request,
        db: Session = Depends(get_db),
        year: int = Query(2024),
    ) -> dict[str, Any]:
        rows = list(db.scalars(
            select(FireCapabilityAsset)
            .where(FireCapabilityAsset.year == year)
            .order_by(FireCapabilityAsset.asset_type, FireCapabilityAsset.id)
        ).all())
        by_type: dict[str, int] = {}
        items = []
        for row in rows:
            by_type[row.asset_type] = by_type.get(row.asset_type, 0) + 1
            items.append({
                "id": row.id,
                "asset_type": row.asset_type,
                "name": row.name,
                "ownership": row.ownership,
                "quantity": row.quantity,
                "is_preventive": row.is_preventive,
                "acquired_via": row.acquired_via,
                "source_id": row.source_id,
            })
        return {
            "year": year,
            "preventive_assets": sum(bool(row.is_preventive) for row in rows),
            "reactive_rentals": sum(
                row.ownership == "rented" and not row.is_preventive for row in rows
            ),
            "by_type": by_type,
            "items": items,
        }

    @router.get("/links")
    @limiter.limit(f"{rate}/minute")
    def list_fire_links(
        request: Request,
        db: Session = Depends(get_db),
        from_type: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        stmt = select(FireLink).order_by(FireLink.id)
        if from_type:
            stmt = stmt.where(FireLink.from_type == from_type)
        return [
            {
                "id": r.id,
                "from_type": r.from_type,
                "from_id": r.from_id,
                "to_type": r.to_type,
                "to_id": r.to_id,
                "strength": r.strength,
                "note": r.note,
                "evidence": r.evidence or {},
            }
            for r in db.scalars(stmt).all()
        ]

    return router
