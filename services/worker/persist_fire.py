"""Persist fire-domain staging records into the ledger tables."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from common.dates import parse_date_flexible
from common.fire.classify import attribution_amount, classify_fire_text, is_fire_related
from common.fuzzy import canonicalize_name
from common.money import parse_money
from schema.models import (
    ActiveFireDetection,
    Document,
    EmergencyDeclaration,
    FireAttribution,
    FireClassificationRun,
    FireCycle,
    FireExpenditure,
    FireSeason,
    IngestionRun,
    OperationalOutput,
    Territory,
    TerritoryLevel,
)
from worker.adapters.base import StagingRecord
from worker.persist import get_or_create_entity, get_or_create_supplier


def get_or_create_territory(
    session: Session,
    name: str,
    *,
    level: str = "departamento",
    parent_id: int | None = None,
    slug: str | None = None,
) -> Territory:
    s = slug or canonicalize_name(name).replace(" ", "-")[:128]
    found = session.scalars(select(Territory).where(Territory.slug == s)).first()
    if found:
        return found
    level_map = {
        "pais": TerritoryLevel.pais,
        "departamento": TerritoryLevel.departamento,
        "municipio": TerritoryLevel.municipio,
    }
    t = Territory(
        name=name,
        slug=s,
        level=level_map.get(level, TerritoryLevel.departamento),
        parent_id=parent_id,
    )
    session.add(t)
    session.flush()
    return t


def get_or_create_season(
    session: Session,
    year: int,
    *,
    start_date=None,
    end_date=None,
    quality_grade: str = "D",
    notes: str | None = None,
) -> FireSeason:
    found = session.scalars(select(FireSeason).where(FireSeason.year == year)).first()
    if found:
        return found
    season = FireSeason(
        year=year,
        start_date=start_date,
        end_date=end_date,
        quality_grade=quality_grade,
        notes=notes,
    )
    session.add(season)
    session.flush()
    return season


def _next_fire_code(session: Session, year: int) -> str:
    existing = session.scalars(
        select(FireExpenditure.code).where(FireExpenditure.year == year)
    ).all()
    seq = 1
    for code in existing:
        try:
            n = int(str(code).rsplit("-", 1)[-1])
            seq = max(seq, n + 1)
        except ValueError:
            continue
    return f"FIRE-BO-{year}-{seq:06d}"


def persist_fire_staging(
    session: Session,
    records: list[StagingRecord],
    *,
    source_id: str,
    run: IngestionRun,
    classification_run: FireClassificationRun | None = None,
) -> int:
    """Materialize fire_operational, fire_expenditure_candidate, emergency_declaration."""
    count = 0
    for rec in records:
        d = rec.data
        if rec.record_type == "fire_operational":
            year = int(d.get("year") or 2024)
            season = get_or_create_season(session, year)
            entity = None
            if d.get("entity_name"):
                entity = get_or_create_entity(
                    session,
                    d["entity_name"],
                    level=d.get("level") or "nacional",
                    source_id=source_id,
                    run_id=run.id,
                )
            territory = None
            if d.get("territory_name"):
                territory = get_or_create_territory(
                    session,
                    d["territory_name"],
                    level=d.get("territory_level") or "departamento",
                )
            session.add(
                OperationalOutput(
                    year=year,
                    season_id=season.id,
                    entity_id=entity.id if entity else None,
                    territory_id=territory.id if territory else None,
                    metric_key=d.get("metric_key") or "unknown",
                    metric_label=d.get("metric_label") or d.get("metric_key") or "Métrica",
                    value_numeric=parse_money(d.get("value_numeric")),
                    value_text=d.get("value_text"),
                    unit=d.get("unit"),
                    document_id=d.get("document_id"),
                    evidence_page=d.get("evidence_page"),
                    evidence_quote=d.get("evidence_quote"),
                    source_id=source_id,
                )
            )
            count += 1

        elif rec.record_type == "fire_expenditure_candidate":
            year = int(d.get("year") or 2024)
            season = get_or_create_season(session, year)
            clf = classify_fire_text(
                object_description=d.get("object_description") or d.get("title"),
                modality=d.get("modality"),
                program_project=d.get("program_project"),
                title=d.get("title"),
                force_direct=bool(d.get("force_direct")),
            )
            if d.get("attribution"):
                attribution = d["attribution"]
                confidence = Decimal(str(d.get("confidence_score") or clf.confidence_score))
                method = d.get("classification_method") or clf.classification_method
                cycle = d.get("cycle") or clf.cycle
            else:
                if not is_fire_related(clf) and not d.get("force_include"):
                    continue
                attribution = clf.attribution
                confidence = clf.confidence_score
                method = clf.classification_method
                cycle = clf.cycle

            entity = None
            if d.get("entity_name"):
                entity = get_or_create_entity(
                    session,
                    d["entity_name"],
                    level=d.get("level") or "nacional",
                    source_id=source_id,
                    run_id=run.id,
                    department=d.get("department"),
                )
            supplier = get_or_create_supplier(
                session,
                d.get("supplier_name"),
                nit=d.get("supplier_nit"),
                source_id=source_id,
                run_id=run.id,
            )
            territory = None
            if d.get("territory_name"):
                territory = get_or_create_territory(
                    session,
                    d["territory_name"],
                    level=d.get("territory_level") or "departamento",
                )

            amount_contract = parse_money(d.get("amount") or d.get("amount_contract"))
            amount_attr = parse_money(d.get("amount_attributed"))
            if amount_attr is None:
                amount_attr = attribution_amount(
                    amount=amount_contract,
                    attribution=attribution,
                    partial_ratio=parse_money(d.get("partial_ratio")),
                )

            code = d.get("code") or _next_fire_code(session, year)
            existing = session.scalars(
                select(FireExpenditure).where(FireExpenditure.code == code)
            ).first()
            if existing:
                existing.title = d.get("title") or existing.title
                existing.amount_contract = amount_contract or existing.amount_contract
                existing.amount_attributed = amount_attr if amount_attr is not None else existing.amount_attributed
                existing.evidence = d.get("evidence") or existing.evidence
                count += 1
                continue

            session.add(
                FireExpenditure(
                    code=code,
                    year=year,
                    season_id=season.id,
                    title=d.get("title") or d.get("object_description") or code,
                    object_description=d.get("object_description"),
                    attribution=FireAttribution(attribution),
                    confidence_score=confidence,
                    classification_method=method,
                    cycle=FireCycle(cycle if cycle in FireCycle.__members__ else "respuesta"),
                    paying_entity_id=entity.id if entity else None,
                    beneficiary_territory_id=territory.id if territory else None,
                    supplier_id=supplier.id if supplier else None,
                    contract_id=d.get("contract_id"),
                    budget_line_id=d.get("budget_line_id"),
                    document_id=d.get("document_id"),
                    classification_run_id=classification_run.id if classification_run else None,
                    amount_contract=amount_contract,
                    amount_attributed=amount_attr,
                    quality_grade=d.get("quality_grade") or "D",
                    cuce=d.get("cuce"),
                    evidence=d.get("evidence") or {
                        "matched_terms": clf.matched_terms,
                        "reason": clf.reason,
                    },
                    source_id=source_id,
                )
            )
            session.flush()
            count += 1

        elif rec.record_type == "emergency_declaration":
            entity = None
            if d.get("entity_name"):
                entity = get_or_create_entity(
                    session, d["entity_name"], source_id=source_id, run_id=run.id
                )
            territory = None
            if d.get("territory_name"):
                territory = get_or_create_territory(
                    session,
                    d["territory_name"],
                    level=d.get("territory_level") or "departamento",
                )
            session.add(
                EmergencyDeclaration(
                    title=d.get("title") or "Declaratoria",
                    decree_number=d.get("decree_number"),
                    event_type=d.get("event_type") or "incendio_forestal",
                    entity_id=entity.id if entity else None,
                    territory_id=territory.id if territory else None,
                    promulgated_at=parse_date_flexible(d.get("promulgated_at")),
                    published_at=parse_date_flexible(d.get("published_at")),
                    url=d.get("url"),
                    document_id=d.get("document_id"),
                    summary=d.get("summary"),
                    source_id=source_id,
                )
            )
            count += 1

        elif rec.record_type == "document":
            session.add(
                Document(
                    url=d.get("url") or "",
                    mime=d.get("mime"),
                    minio_key=d.get("minio_key"),
                    sha256=d.get("sha256") or d.get("raw_sha256"),
                    source_id=source_id,
                    ingestion_run_id=run.id,
                )
            )
            count += 1

        elif rec.record_type == "active_fire_detection":
            year = int(d.get("year") or 2024)
            territory = None
            if d.get("department"):
                territory = get_or_create_territory(
                    session, d["department"], level="departamento"
                )
            session.add(
                ActiveFireDetection(
                    year=year,
                    acq_date=parse_date_flexible(d.get("acq_date")),
                    latitude=parse_money(d.get("latitude")),
                    longitude=parse_money(d.get("longitude")),
                    brightness=parse_money(d.get("brightness")),
                    frp=parse_money(d.get("frp")),
                    confidence=str(d["confidence"]) if d.get("confidence") is not None else None,
                    satellite=d.get("satellite"),
                    department=d.get("department"),
                    municipality=d.get("municipality"),
                    territory_id=territory.id if territory else None,
                    source_id=source_id,
                )
            )
            count += 1

    return count


def classify_contracts_to_fire(
    session: Session,
    *,
    year: int | None = None,
    source_id: str = "fire_classify",
) -> FireClassificationRun:
    """Scan current contracts and create fire_expenditure candidates for fire-related ones."""
    from schema.models import Contract

    run_meta: dict[str, Any] = {"year": year}
    clf_run = FireClassificationRun(
        status="running",
        method="exact_keyword",
        meta=run_meta,
    )
    session.add(clf_run)
    session.flush()

    q = select(Contract).where(Contract.is_current.is_(True))
    contracts = list(session.scalars(q).all())
    if year:
        contracts = [
            c
            for c in contracts
            if c.contract_date and c.contract_date.year == year
        ]

    ingest = IngestionRun(source_id=source_id, status="running", meta={"kind": "classify_fire"})
    session.add(ingest)
    session.flush()

    candidates: list[StagingRecord] = []
    for c in contracts:
        clf = classify_fire_text(
            object_description=c.object_description,
            modality=c.modality,
        )
        if not is_fire_related(clf):
            continue
        entity_name = c.entity.name if c.entity else None
        supplier_name = c.supplier.name if c.supplier else None
        candidates.append(
            StagingRecord(
                record_type="fire_expenditure_candidate",
                data={
                    "year": (c.contract_date.year if c.contract_date else year or 2024),
                    "title": (c.object_description or c.cuce or f"contract-{c.id}")[:1024],
                    "object_description": c.object_description,
                    "modality": c.modality,
                    "entity_name": entity_name,
                    "supplier_name": supplier_name,
                    "amount": str(c.amount) if c.amount is not None else None,
                    "cuce": c.cuce,
                    "contract_id": c.id,
                    "attribution": clf.attribution,
                    "confidence_score": str(clf.confidence_score),
                    "classification_method": clf.classification_method,
                    "cycle": clf.cycle,
                    "quality_grade": "B",
                    "evidence": {
                        "contract_id": c.id,
                        "matched_terms": clf.matched_terms,
                        "reason": clf.reason,
                    },
                },
            )
        )

    out = persist_fire_staging(
        session,
        candidates,
        source_id=source_id,
        run=ingest,
        classification_run=clf_run,
    )
    clf_run.records_in = len(contracts)
    clf_run.records_out = out
    clf_run.status = "ok"
    clf_run.finished_at = datetime.now(timezone.utc)
    ingest.status = "ok"
    ingest.records_in = len(candidates)
    ingest.records_out = out
    ingest.finished_at = datetime.now(timezone.utc)
    return clf_run
