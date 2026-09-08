from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from schema.models import Alert, BudgetLine, Contract, Discrepancy, Entity, Supplier
from common.data_quality import is_public_row


CONCENTRATION_THRESHOLD = Decimal("0.35")
DIRECT_MODALITY_KEYWORDS = ("directa", "excepción", "excepcion", "emergencia", "excepci")
SPLIT_WINDOW_DAYS = 45
SPLIT_MIN_COUNT = 3

ANOMALY_DISCLAIMER = (
    "Anomalía estadística — no implica corrupción. Puede haber causas legítimas "
    "(emergencia, único proveedor calificado, marco normativo)."
)


def _public_contracts(session: Session) -> list[Any]:
    """Lightweight rows for rule evaluation.

    Full ORM objects with joinedloads take forever on production-sized
    databases (1.5M+ contracts); the rules only need a handful of columns.
    """
    rows = session.execute(
        select(
            Contract.id,
            Contract.entity_id,
            Contract.supplier_id,
            Contract.amount,
            Contract.modality,
            Contract.cuce,
            Contract.contract_date,
            Contract.is_synthetic,
            Contract.source_quality,
            Supplier.nit.label("supplier_nit"),
            Supplier.is_synthetic.label("supplier_is_synthetic"),
        )
        .outerjoin(Supplier, Contract.supplier_id == Supplier.id)
        .where(Contract.is_current.is_(True), Contract.is_synthetic.is_(False))
    ).all()
    return [r for r in rows if is_public_row(r)]


def _name_entity(session: Session, entity_id: int | None) -> str:
    if not entity_id:
        return "entidad desconocida"
    e = session.get(Entity, entity_id)
    return e.name if e else f"entidad #{entity_id}"


def _name_supplier(session: Session, supplier_id: int | None) -> str:
    if not supplier_id:
        return "proveedor desconocido"
    s = session.get(Supplier, supplier_id)
    return s.name if s else f"proveedor #{supplier_id}"


def run_alert_rules(session: Session, *, run_id: int | None = None) -> list[Alert]:
    """Materialize explainable alerts with human-readable names."""
    for old in session.scalars(select(Alert).where(Alert.source_id == "rules")).all():
        session.delete(old)
    session.flush()

    alerts: list[Alert] = []
    contracts = _public_contracts(session)

    by_entity: dict[int, list[Contract]] = defaultdict(list)
    for c in contracts:
        by_entity[c.entity_id].append(c)

    # Rule 1: supplier concentration
    for entity_id, rows in by_entity.items():
        totals: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
        total = Decimal("0")
        for c in rows:
            if c.supplier_id is None or c.amount is None:
                continue
            totals[c.supplier_id] += c.amount
            total += c.amount
        if total <= 0:
            continue
        for supplier_id, amt in totals.items():
            share = amt / total
            if share >= CONCENTRATION_THRESHOLD:
                en = _name_entity(session, entity_id)
                sn = _name_supplier(session, supplier_id)
                alerts.append(
                    Alert(
                        rule_id="supplier_concentration",
                        severity="high",
                        title=f"Concentración: {sn} en {en}",
                        explanation=(
                            f"{sn} concentra {share:.0%} ({amt:,.2f} BOB) de los montos "
                            f"contractuales de {en} en el conjunto actual "
                            f"(umbral {CONCENTRATION_THRESHOLD:.0%}). Fuente: registros consolidados."
                        ),
                        entity_id=entity_id,
                        supplier_id=supplier_id,
                        evidence={
                            "share": float(share),
                            "amount": str(amt),
                            "total": str(total),
                            "threshold": str(CONCENTRATION_THRESHOLD),
                            "entity_name": en,
                            "supplier_name": sn,
                        },
                        source_id="rules",
                        ingestion_run_id=run_id,
                    )
                )

    # Rule 2: recurrent direct awards
    direct_rows: dict[tuple[int, int], list[Contract]] = defaultdict(list)
    for c in contracts:
        if c.supplier_id is None or not c.modality:
            continue
        if any(k in c.modality.lower() for k in DIRECT_MODALITY_KEYWORDS):
            direct_rows[(c.entity_id, c.supplier_id)].append(c)
    for (entity_id, supplier_id), rows in direct_rows.items():
        if len(rows) >= 2:
            en = _name_entity(session, entity_id)
            sn = _name_supplier(session, supplier_id)
            alerts.append(
                Alert(
                    rule_id="recurrent_direct_award",
                    severity="medium",
                    title=f"Adjudicaciones directas recurrentes: {sn}",
                    explanation=(
                        f"{en} tiene {len(rows)} contratos con modalidad directa/excepción/"
                        f"emergencia adjudicados a {sn}."
                    ),
                    entity_id=entity_id,
                    supplier_id=supplier_id,
                    contract_id=rows[0].id,
                    evidence={
                        "count": len(rows),
                        "cuces": [r.cuce for r in rows if r.cuce],
                        "entity_name": en,
                        "supplier_name": sn,
                    },
                    source_id="rules",
                    ingestion_run_id=run_id,
                )
            )

    # Rule 3: zero execution late
    today = date.today()
    budgets = list(
        session.scalars(
            select(BudgetLine).where(
                BudgetLine.is_current.is_(True),
                BudgetLine.is_synthetic.is_(False),
            )
        ).all()
    )
    budgets = [b for b in budgets if is_public_row(b)]
    seen_zero_exec: set[tuple[int, int]] = set()
    for b in budgets:
        past_q3 = (b.year < today.year) or (b.year == today.year and today.month >= 10)
        if not past_q3:
            continue
        cur = b.current_amount or Decimal("0")
        exe = b.executed_amount or Decimal("0")
        if cur >= Decimal("1000000") and exe == 0:
            key = (b.entity_id, b.year)
            if key in seen_zero_exec:
                continue
            seen_zero_exec.add(key)
            en = _name_entity(session, b.entity_id)
            alerts.append(
                Alert(
                    rule_id="zero_execution_late",
                    severity="medium",
                    title=f"Ejecución cero: {en} {b.year}",
                    explanation=(
                        f"{en} en gestión {b.year} tiene presupuesto vigente {cur:,.2f} BOB "
                        f"y ejecución 0 (regla post-Q3)."
                    ),
                    entity_id=b.entity_id,
                    evidence={
                        "year": b.year,
                        "current_amount": str(cur),
                        "executed_amount": str(exe),
                        "entity_name": en,
                        "source_id": b.source_id,
                    },
                    source_id="rules",
                    ingestion_run_id=run_id,
                )
            )

    # Rule 4: source discrepancies
    for d in session.scalars(select(Discrepancy).limit(50)).all():
        en = _name_entity(session, d.entity_id)
        alerts.append(
            Alert(
                rule_id="source_discrepancy",
                severity="low",
                title=f"Discrepancia entre fuentes: {d.concept}",
                explanation=(
                    f"{en}: {d.source_a} reporta {d.amount_a} vs {d.source_b} reporta "
                    f"{d.amount_b} para {d.concept}."
                ),
                entity_id=d.entity_id,
                evidence={
                    "discrepancy_id": d.id,
                    "ref_a": d.ref_a,
                    "ref_b": d.ref_b,
                    "entity_name": en,
                },
                source_id="rules",
                ingestion_run_id=run_id,
            )
        )

    # Rule 5: possible contract splitting (same entity+supplier, many small awards close in time)
    by_pair: dict[tuple[int, int], list[Contract]] = defaultdict(list)
    for c in contracts:
        if c.supplier_id and c.contract_date and c.amount:
            by_pair[(c.entity_id, c.supplier_id)].append(c)
    for (entity_id, supplier_id), rows in by_pair.items():
        rows = sorted(rows, key=lambda x: x.contract_date or date.min)
        if len(rows) < SPLIT_MIN_COUNT:
            continue
        # sliding window
        for i in range(len(rows)):
            window = [rows[i]]
            for j in range(i + 1, len(rows)):
                if rows[j].contract_date and rows[i].contract_date:
                    delta = (rows[j].contract_date - rows[i].contract_date).days
                    if delta <= SPLIT_WINDOW_DAYS:
                        window.append(rows[j])
                    else:
                        break
            if len(window) >= SPLIT_MIN_COUNT:
                avg = sum((c.amount or Decimal("0")) for c in window) / len(window)
                if avg < Decimal("500000"):
                    en = _name_entity(session, entity_id)
                    sn = _name_supplier(session, supplier_id)
                    alerts.append(
                        Alert(
                            rule_id="possible_split_awards",
                            severity="medium",
                            title=f"Posible fraccionamiento: {sn} / {en}",
                            explanation=(
                                f"{len(window)} contratos de {sn} con {en} en ≤{SPLIT_WINDOW_DAYS} días "
                                f"(promedio {avg:,.2f} BOB). Revisar si evitan umbrales de licitación."
                            ),
                            entity_id=entity_id,
                            supplier_id=supplier_id,
                            contract_id=window[0].id,
                            evidence={
                                "count": len(window),
                                "avg_amount": str(avg),
                                "cuces": [c.cuce for c in window if c.cuce],
                                "entity_name": en,
                                "supplier_name": sn,
                            },
                            source_id="rules",
                            ingestion_run_id=run_id,
                        )
                    )
                break

    # Rule 6: high budget, low execution ratio mid-year+
    for b in budgets:
        cur = b.current_amount or Decimal("0")
        exe = b.executed_amount or Decimal("0")
        if cur < Decimal("5000000"):
            continue
        if b.year < today.year or (b.year == today.year and today.month >= 6):
            ratio = (exe / cur) if cur else Decimal("0")
            if ratio < Decimal("0.15"):
                en = _name_entity(session, b.entity_id)
                alerts.append(
                    Alert(
                        rule_id="low_execution_ratio",
                        severity="low",
                        title=f"Baja ejecución: {en} {b.year}",
                        explanation=(
                            f"{en} ejecutó solo {ratio:.0%} de {cur:,.2f} BOB vigentes "
                            f"({exe:,.2f} BOB). Umbral de alerta: <15%."
                        ),
                        entity_id=b.entity_id,
                        evidence={
                            "ratio": float(ratio),
                            "current_amount": str(cur),
                            "executed_amount": str(exe),
                            "year": b.year,
                            "entity_name": en,
                        },
                        source_id="rules",
                        ingestion_run_id=run_id,
                    )
                )

    _append_evidence_rules(session, alerts, contracts, run_id=run_id)

    for a in alerts:
        a.is_synthetic = False
        a.is_official = False
        a.is_inferred = True
        a.source_quality = "INFERRED"
        a.evidence_status = "linked" if a.evidence else "none"
        a.confidence_score = Decimal("0.6")
        a.data_origin = "inferred"
        a.legitimate_causes = [
            "Emergencia o excepción legal",
            "Único proveedor calificado",
            "Datos incompletos en fuente",
            ANOMALY_DISCLAIMER,
        ]
        if a.explanation and "Anomalía" not in a.explanation:
            a.explanation = f"{a.explanation} {ANOMALY_DISCLAIMER}"
        session.add(a)
    session.flush()
    return alerts


MISSING_NIT_AMOUNT_THRESHOLD = Decimal("500000")


def filter_missing_nit_high_amount(contracts: list[Contract]) -> list[Contract]:
    """Contracts with amount >= 500k, non-synthetic, supplier without NIT."""
    out: list[Contract] = []
    for c in contracts:
        if getattr(c, "is_synthetic", False):
            continue
        if c.amount is None or c.amount < MISSING_NIT_AMOUNT_THRESHOLD:
            continue
        if not c.supplier_id:
            continue
        try:
            sup = c.supplier  # ORM object path
        except (KeyError, AttributeError):
            sup = None
        if sup is not None:
            sup_synthetic = getattr(sup, "is_synthetic", False)
            sup_nit = sup.nit
        else:
            # lightweight row path (supplier columns joined by _public_contracts)
            sup_synthetic = getattr(c, "supplier_is_synthetic", False)
            sup_nit = getattr(c, "supplier_nit", None)
        if sup_synthetic:
            continue
        if sup_nit:
            continue
        out.append(c)
    return out


def filter_amount_claim_conflicts(conflicts: list) -> list:
    """Open claim_conflict rows on field=amount; skip synthetic-tagged entities if present."""
    out = []
    for conf in conflicts:
        if getattr(conf, "status", "open") != "open":
            continue
        if getattr(conf, "field", None) != "amount":
            continue
        if getattr(conf, "is_synthetic", False):
            continue
        out.append(conf)
    return out


def _append_evidence_rules(
    session: Session,
    alerts: list[Alert],
    contracts: list[Contract],
    *,
    run_id: int | None,
) -> None:
    """B8 — missing_nit_high_amount + amount_claim_conflict."""
    from schema.models import ClaimConflict

    for c in filter_missing_nit_high_amount(contracts):
        en = _name_entity(session, c.entity_id)
        sn = _name_supplier(session, c.supplier_id)
        alerts.append(
            Alert(
                rule_id="missing_nit_high_amount",
                severity="medium",
                title=f"NIT ausente en monto alto: {sn}",
                explanation=(
                    f"Contrato {c.cuce or c.id} de {en} con {sn} por {c.amount:,.2f} BOB "
                    f"sin NIT del proveedor (umbral ≥{MISSING_NIT_AMOUNT_THRESHOLD:,.0f})."
                ),
                entity_id=c.entity_id,
                supplier_id=c.supplier_id,
                contract_id=c.id,
                evidence={
                    "amount": str(c.amount),
                    "threshold": str(MISSING_NIT_AMOUNT_THRESHOLD),
                    "cuce": c.cuce,
                    "entity_name": en,
                    "supplier_name": sn,
                },
                source_id="rules",
                ingestion_run_id=run_id,
            )
        )

    conflicts = list(
        session.scalars(
            select(ClaimConflict).where(
                ClaimConflict.status == "open",
                ClaimConflict.field == "amount",
            )
        ).all()
    )
    for conf in filter_amount_claim_conflicts(conflicts):
        # Skip if linked contract is synthetic
        if conf.entity_type == "contract":
            contract = session.get(Contract, conf.entity_id)
            if contract and getattr(contract, "is_synthetic", False):
                continue
        alerts.append(
            Alert(
                rule_id="amount_claim_conflict",
                severity="high",
                title=f"Conflicto de monto (claims): {conf.entity_type}#{conf.entity_id}",
                explanation=(
                    f"Hay un claim_conflict abierto sobre el campo amount para "
                    f"{conf.entity_type} #{conf.entity_id} (claims {conf.claim_ids})."
                ),
                contract_id=conf.entity_id if conf.entity_type == "contract" else None,
                evidence={
                    "conflict_id": conf.id,
                    "claim_ids": conf.claim_ids,
                    "entity_type": conf.entity_type,
                    "entity_id": conf.entity_id,
                },
                source_id="rules",
                ingestion_run_id=run_id,
            )
        )
