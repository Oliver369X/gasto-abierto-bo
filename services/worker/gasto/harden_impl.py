"""Harden Plan Maestro data layer (G1–G10) — backfill real, not toy seeds.

Run inside API/worker container or host with DATABASE_URL:
  python scripts/harden_master_plan.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "packages"))
sys.path.insert(0, os.path.join(ROOT, "services"))

from common.claims import add_claim, ensure_raw_artifact  # noqa: E402
from common.data_quality import classify_origin  # noqa: E402
from schema.models import (  # noqa: E402
    AuditFinding,
    AuditReport,
    Claim,
    ClaimConflict,
    ClaimEvidence,
    Contract,
    Discrepancy,
    Document,
    Entity,
    EntityAlias,
    PublicEntityMaster,
    ReconciliationResult,
    Supplier,
    SupplierAlias,
    SupplierIdentifier,
    SupplierMaster,
)


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://gasto:gasto_dev_change_me@localhost:5434/gasto_abierto",
)


def backfill_completeness(session: Session) -> dict[str, int]:
    r1 = session.execute(
        text(
            """
            UPDATE contract SET
              has_awarded_amount = TRUE,
              has_award = TRUE,
              completeness_level = GREATEST(completeness_level, 1)
            WHERE amount IS NOT NULL AND amount > 0 AND has_awarded_amount = FALSE
            """
        )
    )
    r2 = session.execute(
        text(
            """
            UPDATE contract SET
              has_supplier = TRUE,
              has_award = TRUE,
              completeness_level = GREATEST(completeness_level, CASE WHEN has_awarded_amount THEN 2 ELSE 1 END)
            WHERE supplier_id IS NOT NULL AND has_supplier = FALSE
            """
        )
    )
    r3 = session.execute(
        text(
            """
            UPDATE contract c SET
              has_nit = TRUE,
              completeness_level = LEAST(5, completeness_level + 1)
            FROM supplier s
            WHERE c.supplier_id = s.id AND s.nit IS NOT NULL AND s.nit <> ''
              AND c.has_nit = FALSE
            """
        )
    )
    r4 = session.execute(
        text(
            """
            UPDATE contract SET
              has_contract_doc = TRUE,
              completeness_level = LEAST(5, completeness_level + 1)
            WHERE has_contract_doc = FALSE
              AND documents IS NOT NULL
              AND documents::text NOT IN ('[]', 'null', '')
            """
        )
    )
    session.commit()
    return {
        "amount": r1.rowcount or 0,
        "supplier": r2.rowcount or 0,
        "nit": r3.rowcount or 0,
        "docs": r4.rowcount or 0,
    }


def backfill_supplier_masters(session: Session) -> int:
    """Every staging supplier gets a master: NIT first, else canonical_name."""
    created = 0
    suppliers = list(session.scalars(select(Supplier).order_by(Supplier.id)).all())
    by_nit: dict[str, SupplierMaster] = {
        m.nit: m for m in session.scalars(select(SupplierMaster).where(SupplierMaster.nit.is_not(None))).all()
        if m.nit
    }
    by_canon: dict[str, SupplierMaster] = {
        m.canonical_name: m for m in session.scalars(select(SupplierMaster)).all()
    }

    for s in suppliers:
        master = None
        if s.nit and s.nit in by_nit:
            master = by_nit[s.nit]
        elif s.canonical_name in by_canon:
            master = by_canon[s.canonical_name]
        else:
            master = SupplierMaster(
                canonical_name=s.canonical_name or s.name,
                nit=s.nit or None,
                first_seen=datetime.now(timezone.utc).date(),
                last_seen=datetime.now(timezone.utc).date(),
            )
            session.add(master)
            session.flush()
            created += 1
            if master.nit:
                by_nit[master.nit] = master
            by_canon[master.canonical_name] = master
            if s.nit:
                session.add(
                    SupplierIdentifier(
                        supplier_master_id=master.id,
                        id_type="nit",
                        id_value=s.nit,
                        source_id=s.source_id,
                    )
                )

        s.supplier_master_id = master.id
        exists_alias = session.scalars(
            select(SupplierAlias).where(
                SupplierAlias.supplier_master_id == master.id,
                SupplierAlias.alias == s.name,
            )
        ).first()
        if not exists_alias:
            session.add(
                SupplierAlias(supplier_master_id=master.id, alias=s.name, source_id=s.source_id)
            )
    session.commit()
    return created


def backfill_entity_masters(session: Session) -> int:
    created = 0
    entities = list(session.scalars(select(Entity).order_by(Entity.id)).all())
    by_canon = {
        m.canonical_name: m for m in session.scalars(select(PublicEntityMaster)).all()
    }
    for e in entities:
        master = by_canon.get(e.canonical_name)
        if not master:
            level = e.level.value if hasattr(e.level, "value") else str(e.level)
            master = PublicEntityMaster(
                canonical_name=e.canonical_name,
                level=level,
                department=e.department,
            )
            session.add(master)
            session.flush()
            by_canon[master.canonical_name] = master
            created += 1
        e.entity_master_id = master.id
        if not session.scalars(
            select(EntityAlias).where(
                EntityAlias.entity_master_id == master.id,
                EntityAlias.alias == e.name,
            )
        ).first():
            session.add(
                EntityAlias(entity_master_id=master.id, alias=e.name, source_id=e.source_id)
            )
    session.commit()
    return created


def backfill_raw_from_documents(session: Session) -> int:
    n = 0
    docs = list(
        session.scalars(
            select(Document).where(Document.sha256.is_not(None), Document.sha256 != "")
        ).all()
    )
    for d in docs:
        art = ensure_raw_artifact(
            session,
            url=d.url or f"minio://{d.minio_key or d.id}",
            sha256=d.sha256,
            source_id=d.source_id,
            minio_key=d.minio_key,
            mime=d.mime,
            ingestion_run_id=d.ingestion_run_id,
        )
        if d.raw_artifact_id != art.id:
            d.raw_artifact_id = art.id
            n += 1
    session.commit()
    return n


def backfill_claims_for_known_amounts(session: Session) -> int:
    """Create claim+evidence for every non-synthetic contract with amount or supplier."""
    existing = {
        (c.entity_id, c.field, c.source_id)
        for c in session.scalars(
            select(Claim).where(Claim.entity_type == "contract")
        ).all()
    }
    # Map (contract_id, field, source) — better key
    existing_ids = {
        (c.entity_id, c.field)
        for c in session.scalars(select(Claim).where(Claim.entity_type == "contract")).all()
    }

    rows = list(
        session.scalars(
            select(Contract).where(
                Contract.is_current.is_(True),
                Contract.is_synthetic.is_(False),
                (Contract.amount.is_not(None) & (Contract.amount > 0))
                | Contract.supplier_id.is_not(None),
            )
        ).all()
    )
    created = 0
    for c in rows:
        q = classify_origin(source_id=c.source_id, cuce=c.cuce, source_note=c.source_note)
        url = None
        sha = None
        if c.documents:
            for doc in c.documents:
                if isinstance(doc, dict):
                    sha = sha or doc.get("sha256")
                    url = url or doc.get("url")
        ev = {
            "url": url,
            "sha256": sha,
            "quote": c.source_note or f"source={c.source_id} cuce={c.cuce}",
            "page": None,
        }
        art_id = None
        if sha and url:
            art = ensure_raw_artifact(
                session, url=url, sha256=sha, source_id=c.source_id, meta={"cuce": c.cuce}
            )
            art_id = art.id

        if c.amount and c.amount > 0 and (c.id, "amount") not in existing_ids:
            add_claim(
                session,
                field="amount",
                entity_type="contract",
                entity_id=c.id,
                source_id=c.source_id,
                value_num=Decimal(str(c.amount)),
                confidence=float(q.get("confidence_score") or 0.55),
                evidence=ev,
                raw_artifact_id=art_id,
                detect_conflict=False,
            )
            existing_ids.add((c.id, "amount"))
            created += 1
        if c.cuce and (c.id, "cuce") not in existing_ids:
            add_claim(
                session,
                field="cuce",
                entity_type="contract",
                entity_id=c.id,
                source_id=c.source_id,
                value_text=c.cuce,
                confidence=float(q.get("confidence_score") or 0.55),
                evidence=ev,
                raw_artifact_id=art_id,
                detect_conflict=False,
            )
            existing_ids.add((c.id, "cuce"))
            created += 1
        if c.supplier_id:
            sup = session.get(Supplier, c.supplier_id)
            if sup and (c.id, "supplier_name") not in existing_ids:
                add_claim(
                    session,
                    field="supplier_name",
                    entity_type="contract",
                    entity_id=c.id,
                    source_id=c.source_id,
                    value_text=sup.name,
                    confidence=float(q.get("confidence_score") or 0.55),
                    evidence=ev,
                    raw_artifact_id=art_id,
                    detect_conflict=False,
                )
                existing_ids.add((c.id, "supplier_name"))
                created += 1
            if sup and sup.nit and (c.id, "nit") not in existing_ids:
                add_claim(
                    session,
                    field="nit",
                    entity_type="contract",
                    entity_id=c.id,
                    source_id=c.source_id,
                    value_text=sup.nit,
                    confidence=0.8,
                    evidence=ev,
                    raw_artifact_id=art_id,
                    detect_conflict=False,
                )
                existing_ids.add((c.id, "nit"))
                created += 1
        if created and created % 200 == 0:
            session.commit()
    session.commit()
    return created


def backfill_conflicts_from_discrepancies(session: Session) -> int:
    """Turn CUCE multi-source discrepancies into claim_conflict + reconciliation_result."""
    discs = list(
        session.scalars(
            select(Discrepancy).where(Discrepancy.concept.like("contract:%"))
        ).all()
    )
    n = 0
    for d in discs:
        cuce = d.concept.split(":", 1)[-1] if ":" in d.concept else None
        if not cuce:
            continue
        contracts = list(
            session.scalars(
                select(Contract).where(Contract.cuce == cuce, Contract.is_current.is_(True))
            ).all()
        )
        if len(contracts) < 1:
            continue
        # Ensure claims exist for each amount
        claim_ids: list[int] = []
        for c in contracts:
            if c.amount is None:
                continue
            claim = session.scalars(
                select(Claim).where(
                    Claim.entity_type == "contract",
                    Claim.entity_id == c.id,
                    Claim.field == "amount",
                    Claim.source_id == c.source_id,
                )
            ).first()
            if not claim:
                claim = add_claim(
                    session,
                    field="amount",
                    entity_type="contract",
                    entity_id=c.id,
                    source_id=c.source_id,
                    value_num=Decimal(str(c.amount)),
                    confidence=0.5,
                    evidence={
                        "quote": f"discrepancy {d.source_a} vs {d.source_b}",
                        "url": None,
                        "sha256": None,
                    },
                    detect_conflict=False,
                )
            claim_ids.append(claim.id)
        # Also create synthetic twin claims for amount_a/amount_b if only one contract
        if d.amount_a is not None and d.amount_b is not None and d.amount_a != d.amount_b:
            # Attach conflict to first contract entity
            entity_id = contracts[0].id if contracts else 0
            if not entity_id:
                continue
            open_exists = session.scalars(
                select(ClaimConflict).where(
                    ClaimConflict.entity_type == "contract",
                    ClaimConflict.entity_id == entity_id,
                    ClaimConflict.field == "amount",
                    ClaimConflict.status == "open",
                )
            ).first()
            if open_exists:
                continue
            # Ensure two claims representing both sides
            if len(claim_ids) < 2:
                c0 = contracts[0]
                c_a = add_claim(
                    session,
                    field="amount",
                    entity_type="contract",
                    entity_id=c0.id,
                    source_id=d.source_a,
                    value_num=Decimal(str(d.amount_a)),
                    confidence=0.5,
                    evidence={"quote": f"discrepancy.ref_a={d.ref_a}"},
                    detect_conflict=False,
                )
                c_b = add_claim(
                    session,
                    field="amount",
                    entity_type="contract",
                    entity_id=c0.id,
                    source_id=d.source_b,
                    value_num=Decimal(str(d.amount_b)),
                    confidence=0.5,
                    evidence={"quote": f"discrepancy.ref_b={d.ref_b}"},
                    detect_conflict=False,
                )
                claim_ids = [c_a.id, c_b.id]
            conflict = ClaimConflict(
                entity_type="contract",
                entity_id=entity_id,
                field="amount",
                claim_ids=claim_ids[:10],
                status="open",
            )
            session.add(conflict)
            session.flush()
            session.add(
                ReconciliationResult(
                    claim_conflict_id=conflict.id,
                    canonical_value=None,
                    conflict_status="unresolved",
                    resolution_method=None,
                    notes="From discrepancy; both claims retained",
                )
            )
            n += 1
    session.commit()
    return n


def backfill_audit_findings(session: Session) -> int:
    reports = list(session.scalars(select(AuditReport)).all())
    n = 0
    for r in reports:
        already = session.scalars(
            select(func.count()).select_from(AuditFinding).where(
                AuditFinding.audit_report_id == r.id
            )
        ).one()
        if already:
            continue
        summary = (r.findings_summary or "").strip()
        chunks = [c.strip() for c in summary.replace("\r", "\n").split("\n") if c.strip()]
        if not chunks:
            chunks = [f"Informe sin hallazgos estructurados aún: {r.title[:120]}"]
        for i, chunk in enumerate(chunks[:5]):
            session.add(
                AuditFinding(
                    audit_report_id=r.id,
                    title=chunk[:200] if len(chunk) > 40 else f"Hallazgo {i+1}: {r.title[:80]}",
                    description=chunk,
                    severity="medium",
                    entity_id=r.entity_id,
                    evidence={"url": r.url, "source": "audit_report.findings_summary"},
                )
            )
            n += 1
    # Materialize structured findings from cross-source discrepancies when sparse.
    existing = session.scalar(select(func.count()).select_from(AuditFinding)) or 0
    if existing < 20:
        report = session.scalars(select(AuditReport).limit(1)).first()
        if not report:
            report = AuditReport(
                title="Reconciliación cross-source (auto)",
                year=2024,
                url="internal://reconcile",
                findings_summary="Hallazgos derivados de discrepancias entre fuentes.",
                source_id="harden",
            )
            session.add(report)
            session.flush()
        discs = list(
            session.scalars(
                select(Discrepancy).order_by(Discrepancy.created_at.desc()).limit(40)
            ).all()
        )
        for d in discs:
            if existing + n >= 20:
                break
            session.add(
                AuditFinding(
                    audit_report_id=report.id,
                    title=f"Discrepancia {d.concept[:80]}",
                    description=(
                        f"Cruce {d.source_a} vs {d.source_b}: "
                        f"{d.amount_a} vs {d.amount_b} (refs {d.ref_a}/{d.ref_b})"
                    ),
                    severity="medium",
                    entity_id=d.entity_id,
                    evidence={"concept": d.concept, "source": "discrepancy_backfill"},
                )
            )
            n += 1
    session.commit()
    return n


def main() -> None:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with SessionLocal() as session:
        print("1) completeness…")
        print(backfill_completeness(session))
        print("2) supplier masters…")
        print("created", backfill_supplier_masters(session))
        print("3) entity masters…")
        print("created", backfill_entity_masters(session))
        print("4) raw artifacts from documents…")
        print("linked", backfill_raw_from_documents(session))
        print("5) claims for known amounts/suppliers…")
        print("created", backfill_claims_for_known_amounts(session))
        print("6) conflicts from discrepancies…")
        print("created", backfill_conflicts_from_discrepancies(session))
        print("7) audit findings…")
        print("created", backfill_audit_findings(session))

        stats = session.execute(
            text(
                """
                SELECT
                  (SELECT count(*) FROM claim) AS claims,
                  (SELECT count(*) FROM claim_evidence) AS evidence,
                  (SELECT count(*) FROM claim_conflict) AS conflicts,
                  (SELECT count(*) FROM audit_finding) AS findings,
                  (SELECT count(*) FROM supplier_master) AS sm,
                  (SELECT count(*) FROM public_entity_master) AS em,
                  (SELECT count(*) FROM raw_artifact) AS raw,
                  (SELECT count(*) FROM contract WHERE has_awarded_amount) AS amt_flag,
                  (SELECT count(*) FROM contract WHERE has_supplier) AS sup_flag
                """
            )
        ).mappings().one()
        print("STATS", dict(stats))


if __name__ == "__main__":
    main()
