from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from common.categorize import categorize
from common.claims import add_claim, ensure_raw_artifact
from common.data_quality import classify_origin
from common.dates import parse_date_flexible
from common.cuce import normalize_cuce
from common.discrepancy import build_discrepancy
from common.fuzzy import canonicalize_name, best_match
from common.money import parse_money
from common.scd2 import upsert_versioned
from schema.models import (
    AdminLevel,
    AuditReport,
    BudgetLine,
    Contract,
    Discrepancy,
    Document,
    Entity,
    IngestionRun,
    Supplier,
)
from worker.adapters.base import StagingRecord
from worker.enrich_sicoes import apply_completeness


def start_run(session: Session, source_id: str, meta: dict | None = None) -> IngestionRun:
    run = IngestionRun(source_id=source_id, status="running", meta=meta or {})
    session.add(run)
    session.flush()
    return run


def finish_run(
    session: Session,
    run: IngestionRun,
    *,
    status: str = "ok",
    records_in: int = 0,
    records_out: int = 0,
    error: str | None = None,
) -> None:
    run.status = status
    run.records_in = records_in
    run.records_out = records_out
    run.error_message = error
    run.finished_at = datetime.now(timezone.utc)


def _level(value: str | None) -> AdminLevel:
    mapping = {
        "nacional": AdminLevel.nacional,
        "departamental": AdminLevel.departamental,
        "municipal": AdminLevel.municipal,
        "empresarial": AdminLevel.empresarial,
    }
    if not value:
        return AdminLevel.nacional
    return mapping.get(value.lower(), AdminLevel.nacional)


def get_or_create_entity(
    session: Session,
    name: str,
    *,
    level: str | None = None,
    source_id: str,
    run_id: int | None,
    department: str | None = None,
) -> Entity:
    canon = canonicalize_name(name)
    existing = list(session.scalars(select(Entity)).all())
    by_canon = {e.canonical_name: e for e in existing}
    if canon in by_canon:
        return by_canon[canon]
    match = best_match(name, [e.name for e in existing], score_cutoff=90)
    if match:
        for e in existing:
            if e.name == match[0]:
                return e
    q = classify_origin(source_id=source_id)
    ent = Entity(
        name=name,
        canonical_name=canon,
        level=_level(level),
        aliases=[],
        department=department,
        source_id=source_id,
        ingestion_run_id=run_id,
        **q,
    )
    session.add(ent)
    session.flush()
    return ent


def get_or_create_supplier(
    session: Session,
    name: str | None,
    *,
    nit: str | None = None,
    source_id: str,
    run_id: int | None,
) -> Supplier | None:
    if not name:
        return None
    if nit:
        found = session.scalars(select(Supplier).where(Supplier.nit == nit)).first()
        if found:
            _link_supplier_master(session, found)
            return found
    existing = list(session.scalars(select(Supplier)).all())
    match = best_match(name, [s.name for s in existing], score_cutoff=90)
    if match:
        for s in existing:
            if s.name == match[0]:
                if nit and not s.nit:
                    s.nit = nit
                _link_supplier_master(session, s)
                return s
    q = classify_origin(source_id=source_id)
    sup = Supplier(
        name=name,
        canonical_name=canonicalize_name(name),
        nit=nit,
        aliases=[],
        source_id=source_id,
        ingestion_run_id=run_id,
        **q,
    )
    session.add(sup)
    session.flush()
    _link_supplier_master(session, sup)
    return sup


def _link_supplier_master(session: Session, supplier: Supplier) -> None:
    """Create/link SupplierMaster when supplier has NIT (B7)."""
    from schema.models import SupplierIdentifier, SupplierMaster

    if not supplier.nit:
        return
    if supplier.supplier_master_id:
        return
    master = session.scalars(
        select(SupplierMaster).where(SupplierMaster.nit == supplier.nit)
    ).first()
    if not master:
        master = session.scalars(
            select(SupplierMaster).where(
                SupplierMaster.canonical_name == supplier.canonical_name
            )
        ).first()
    if not master:
        master = SupplierMaster(
            canonical_name=supplier.canonical_name or supplier.name,
            nit=supplier.nit,
            first_seen=datetime.now(timezone.utc).date(),
            last_seen=datetime.now(timezone.utc).date(),
        )
        session.add(master)
        session.flush()
        session.add(
            SupplierIdentifier(
                supplier_master_id=master.id,
                id_type="nit",
                id_value=supplier.nit,
                source_id=supplier.source_id,
            )
        )
    elif not master.nit:
        master.nit = supplier.nit
    supplier.supplier_master_id = master.id
    session.flush()


def _emit_contract_claims(
    session: Session,
    contract: Contract,
    *,
    source_id: str,
    cuce: str | None,
    amount,
    supplier: Supplier | None,
    source_url: str | None = None,
    raw_sha256: str | None = None,
    source_note: str | None = None,
    minio_key: str | None = None,
    ingestion_run_id: int | None = None,
    detect_conflict_amount: bool = False,
) -> None:
    """Emit claims for a contract version (insert or SCD2 / soft-fill)."""
    art_id = None
    if raw_sha256 and (source_url or minio_key):
        art = ensure_raw_artifact(
            session,
            url=source_url or f"minio://{minio_key}",
            sha256=raw_sha256,
            source_id=source_id,
            minio_key=minio_key,
            ingestion_run_id=ingestion_run_id,
        )
        art_id = art.id
    ev_base = {
        "url": source_url,
        "sha256": raw_sha256,
        "quote": source_note,
    }
    q = classify_origin(source_id=source_id, cuce=cuce, source_note=source_note)
    add_claim(
        session,
        field="cuce",
        entity_type="contract",
        entity_id=contract.id,
        source_id=source_id,
        value_text=cuce,
        confidence=q.get("confidence_score"),
        evidence=ev_base,
        raw_artifact_id=art_id,
        detect_conflict=False,
    )
    if amount is not None:
        add_claim(
            session,
            field="amount",
            entity_type="contract",
            entity_id=contract.id,
            source_id=source_id,
            value_num=amount,
            confidence=q.get("confidence_score"),
            evidence=ev_base,
            raw_artifact_id=art_id,
            detect_conflict=detect_conflict_amount,
        )
    if supplier:
        add_claim(
            session,
            field="supplier_name",
            entity_type="contract",
            entity_id=contract.id,
            source_id=source_id,
            value_text=supplier.name,
            confidence=q.get("confidence_score"),
            evidence=ev_base,
            raw_artifact_id=art_id,
        )
        if supplier.nit:
            add_claim(
                session,
                field="nit",
                entity_type="contract",
                entity_id=contract.id,
                source_id=source_id,
                value_text=supplier.nit,
                confidence=q.get("confidence_score"),
                evidence=ev_base,
                raw_artifact_id=art_id,
            )


def _get_or_create_entity_cached(
    session: Session,
    cache: dict[str, Entity],
    name: str,
    *,
    level: str | None = None,
    source_id: str,
    run_id: int | None,
    department: str | None = None,
) -> Entity:
    canon = canonicalize_name(name)
    if canon in cache:
        return cache[canon]
    q = classify_origin(source_id=source_id)
    ent = Entity(
        name=name,
        canonical_name=canon,
        level=_level(level),
        aliases=[],
        department=department,
        source_id=source_id,
        ingestion_run_id=run_id,
        **q,
    )
    session.add(ent)
    session.flush()
    cache[canon] = ent
    return ent


def _get_or_create_supplier_cached(
    session: Session,
    cache: dict[str, Supplier],
    name: str | None,
    *,
    nit: str | None = None,
    source_id: str,
    run_id: int | None,
) -> Supplier | None:
    if not name:
        return None
    canon = canonicalize_name(name)
    if canon in cache:
        s = cache[canon]
        if nit and not s.nit:
            s.nit = nit
            _link_supplier_master(session, s)
        return s
    if nit:
        found = session.scalars(select(Supplier).where(Supplier.nit == nit)).first()
        if found:
            cache[canon] = found
            _link_supplier_master(session, found)
            return found
    q = classify_origin(source_id=source_id)
    sup = Supplier(
        name=name,
        canonical_name=canon,
        nit=nit,
        aliases=[],
        source_id=source_id,
        ingestion_run_id=run_id,
        **q,
    )
    session.add(sup)
    session.flush()
    _link_supplier_master(session, sup)
    cache[canon] = sup
    return sup


def _budget_equal(current: BudgetLine, values: dict[str, Any]) -> bool:
    keys = (
        "initial_amount",
        "modified_amount",
        "current_amount",
        "executed_amount",
        "program_project",
        "budget_item",
    )
    return all(getattr(current, k, None) == values.get(k) for k in keys)


def persist_staging(
    session: Session,
    records: list[StagingRecord],
    *,
    source_id: str,
    run: IngestionRun,
) -> int:
    count = 0
    now = datetime.now(timezone.utc)
    # Bulk caches — avoid O(n²) full-table scans on large history seeds
    entity_cache: dict[str, Entity] = {
        e.canonical_name: e for e in session.scalars(select(Entity)).all()
    }
    supplier_cache: dict[str, Supplier] = {
        s.canonical_name: s for s in session.scalars(select(Supplier)).all()
    }
    # Avoid UniqueViolation when same CUCE appears twice in one batch
    # or when SCD2 close+reopen happens before flush.
    batch_cuce: set[str] = set()
    for rec in records:
        d = rec.data
        if rec.record_type == "contract":
            entity = _get_or_create_entity_cached(
                session,
                entity_cache,
                d.get("entity_name") or "Entidad desconocida",
                source_id=source_id,
                run_id=run.id,
                department=d.get("department"),
                level=d.get("level"),
            )
            supplier = _get_or_create_supplier_cached(
                session,
                supplier_cache,
                d.get("supplier_name"),
                nit=d.get("supplier_nit"),
                source_id=source_id,
                run_id=run.id,
            )
            amount = parse_money(d.get("amount"))
            cuce = normalize_cuce(d.get("cuce"))
            amount_changed = False

            # Cross-source discrepancy: same normalized CUCE, different source/amount
            if cuce and amount is not None:
                others = session.scalars(
                    select(Contract).where(
                        Contract.cuce == cuce,
                        Contract.is_current.is_(True),
                        Contract.source_id != source_id,
                    )
                ).all()
                for other in others:
                    disc = build_discrepancy(
                        concept=f"contract:{cuce}",
                        entity_id=entity.id,
                        amount_a=other.amount,
                        amount_b=amount,
                        source_a=other.source_id,
                        source_b=source_id,
                        ref_a=str(other.id),
                        ref_b=cuce,
                    )
                    if disc:
                        session.add(Discrepancy(**disc))

            if cuce:
                if cuce in batch_cuce:
                    # Duplicate in same ingest payload — skip second insert
                    count += 1
                    continue
                existing = session.scalars(
                    select(Contract).where(
                        Contract.cuce == cuce,
                        Contract.source_id == source_id,
                        Contract.is_current.is_(True),
                    )
                ).first()
                if existing:
                    if existing.amount is not None and amount is not None:
                        disc = build_discrepancy(
                            concept=f"contract:{cuce}",
                            entity_id=entity.id,
                            amount_a=existing.amount,
                            amount_b=amount,
                            source_a=existing.source_id,
                            source_b=source_id,
                            ref_a=str(existing.id),
                        )
                        if disc:
                            session.add(Discrepancy(**disc))
                    new_date = parse_date_flexible(d.get("contract_date"))
                    soft_fill_amount = existing.amount is None and amount is not None
                    soft_fill_supplier = existing.supplier_id is None and supplier is not None
                    amount_ok = existing.amount == amount or soft_fill_amount
                    unchanged = (
                        amount_ok
                        and (existing.object_description or "")
                        == (d.get("object_description") or "")
                        and (existing.modality or "") == (d.get("modality") or "")
                        and existing.contract_date == new_date
                        and existing.entity_id == entity.id
                    )
                    if unchanged:
                        existing.ingestion_run_id = run.id
                        existing.category = categorize(
                            object_description=d.get("object_description"),
                            modality=d.get("modality"),
                        )
                        if soft_fill_amount:
                            existing.amount = amount
                        if soft_fill_supplier and supplier:
                            existing.supplier_id = supplier.id
                        if d.get("minio_key"):
                            docs = list(existing.documents or [])
                            docs.append(
                                {"minio_key": d["minio_key"], "sha256": d.get("raw_sha256")}
                            )
                            existing.documents = docs
                        if soft_fill_amount or soft_fill_supplier:
                            apply_completeness(session, existing)
                            _emit_contract_claims(
                                session,
                                existing,
                                source_id=source_id,
                                cuce=cuce,
                                amount=amount if soft_fill_amount else None,
                                supplier=supplier if soft_fill_supplier else None,
                                source_url=d.get("source_url"),
                                raw_sha256=d.get("raw_sha256"),
                                source_note=d.get("source_note"),
                                minio_key=d.get("minio_key"),
                                ingestion_run_id=run.id,
                                detect_conflict_amount=False,
                            )
                        batch_cuce.add(cuce)
                        count += 1
                        continue
                    amount_changed = (
                        existing.amount is not None
                        and amount is not None
                        and existing.amount != amount
                    )
                    existing.is_current = False
                    existing.valid_to = now
                    session.flush()  # release partial unique before insert

            docs = list(d.get("documents") or [])
            if d.get("minio_key"):
                docs.append({"minio_key": d["minio_key"], "sha256": d.get("raw_sha256")})

            cat = categorize(
                object_description=d.get("object_description"),
                modality=d.get("modality"),
            )
            source_note = d.get("source_note")
            q = classify_origin(source_id=source_id, cuce=cuce, source_note=source_note)
            contract = Contract(
                cuce=cuce,
                entity_id=entity.id,
                supplier_id=supplier.id if supplier else None,
                object_description=d.get("object_description"),
                modality=d.get("modality"),
                category=cat,
                amount=amount,
                contract_date=parse_date_flexible(d.get("contract_date")),
                status=d.get("status"),
                documents=docs,
                source_id=source_id,
                ingestion_run_id=run.id,
                valid_from=now,
                is_current=True,
                source_note=source_note,
                **q,
            )
            session.add(contract)
            session.flush()
            apply_completeness(session, contract)

            _emit_contract_claims(
                session,
                contract,
                source_id=source_id,
                cuce=cuce,
                amount=amount,
                supplier=supplier,
                source_url=d.get("source_url"),
                raw_sha256=d.get("raw_sha256"),
                source_note=source_note,
                minio_key=d.get("minio_key"),
                ingestion_run_id=run.id,
                detect_conflict_amount=amount_changed,
            )
            if cuce:
                batch_cuce.add(cuce)
            count += 1
            if count % 2000 == 0:
                session.flush()
        elif rec.record_type == "budget":
            entity = _get_or_create_entity_cached(
                session,
                entity_cache,
                d.get("entity_name") or "Entidad desconocida",
                level=d.get("level"),
                source_id=source_id,
                run_id=run.id,
                department=d.get("department"),
            )
            year = int(d.get("year") or 2025)
            initial = parse_money(d.get("initial_amount")) or None
            modified = parse_money(d.get("modified_amount")) or None
            current = parse_money(d.get("current_amount")) or None
            executed = parse_money(d.get("executed_amount")) or None
            q = classify_origin(source_id=source_id, source_note=d.get("source_note"))
            values = {
                "program_project": d.get("program_project"),
                "budget_item": d.get("budget_item"),
                "category": categorize(
                    object_description=d.get("program_project"),
                    budget_item=d.get("budget_item"),
                    program_project=d.get("program_project"),
                ),
                "initial_amount": initial,
                "modified_amount": modified,
                "current_amount": current,
                "executed_amount": executed,
                # G6 phases — same semantic slots, never summed as independent totals
                "budget_initial": initial,
                "budget_modification": modified,
                "budget_current": current,
                "commitment": parse_money(d.get("commitment")) or None,
                "accrual": parse_money(d.get("accrual")) or None,
                "payment": executed if d.get("payment") is None else parse_money(d.get("payment")),
                "budget_phase": d.get("budget_phase") or "mapped",
                "currency": d.get("currency") or "BOB",
                "as_of": parse_date_flexible(d.get("as_of")),
                "ingestion_run_id": run.id,
                "source_note": d.get("source_note"),
                **q,
            }
            upsert_versioned(
                session,
                BudgetLine,
                {"entity_id": entity.id, "year": year, "source_id": source_id},
                values,
                equal_fn=_budget_equal,
            )
            count += 1
        elif rec.record_type == "audit":
            entity = None
            if d.get("entity_name"):
                entity = get_or_create_entity(
                    session, d["entity_name"], source_id=source_id, run_id=run.id
                )
            aq = classify_origin(source_id=source_id, source_note=d.get("source_note"))
            session.add(
                AuditReport(
                    entity_id=entity.id if entity else None,
                    title=d.get("title") or "Informe",
                    year=d.get("year"),
                    url=d.get("url") or "",
                    findings_summary=d.get("findings_summary"),
                    source_id=source_id,
                    ingestion_run_id=run.id,
                    source_note=d.get("source_note"),
                    **aq,
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
        elif rec.record_type in (
            "fire_operational",
            "fire_expenditure_candidate",
            "emergency_declaration",
            "active_fire_detection",
        ):
            from worker.persist_fire import persist_fire_staging

            count += persist_fire_staging(
                session, [rec], source_id=source_id, run=run
            )
    return count
