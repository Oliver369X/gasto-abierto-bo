"""SICOES coverage endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.deps import RATE, get_db, limiter
from api.schemas import CoverageFlagOut, SicoesCoverageOut
from common.data_quality import public_contract_filter
from schema.models import Contract

router = APIRouter()


@router.get("/v1/coverage/sicoes", response_model=SicoesCoverageOut, tags=["quality"])
@limiter.limit(f"{RATE}/minute")
def coverage_sicoes(
    request: Request,
    db: Session = Depends(get_db),
    year_from: int = Query(2024, ge=2007),
) -> SicoesCoverageOut:
    """Coverage: recent catalog sample + universe with known amounts."""

    def flag_counts(sample: list[Contract]) -> tuple[list[CoverageFlagOut], dict[str, bool]]:
        sn = len(sample) or 1
        amt_or_ref = sum(
            1
            for r in sample
            if r.has_awarded_amount or r.has_reference_price or (r.amount and r.amount > 0)
        )
        flags = [
            CoverageFlagOut(
                flag="has_reference_price",
                count=sum(1 for r in sample if r.has_reference_price),
                pct=round(100.0 * sum(1 for r in sample if r.has_reference_price) / sn, 2),
            ),
            CoverageFlagOut(
                flag="has_awarded_amount_or_ref",
                count=amt_or_ref,
                pct=round(100.0 * amt_or_ref / sn, 2),
            ),
            CoverageFlagOut(
                flag="has_supplier",
                count=sum(1 for r in sample if r.has_supplier),
                pct=round(100.0 * sum(1 for r in sample if r.has_supplier) / sn, 2),
            ),
            CoverageFlagOut(
                flag="has_nit",
                count=sum(1 for r in sample if r.has_nit),
                pct=round(100.0 * sum(1 for r in sample if r.has_nit) / sn, 2),
            ),
            CoverageFlagOut(
                flag="has_contract_doc",
                count=sum(1 for r in sample if r.has_contract_doc),
                pct=round(100.0 * sum(1 for r in sample if r.has_contract_doc) / sn, 2),
            ),
        ]
        gate = {
            "has_awarded_amount_or_ref": amt_or_ref / sn >= 0.40,
            "has_supplier": (sum(1 for r in sample if r.has_supplier) / sn) >= 0.30,
        }
        return flags, gate

    rows = list(
        db.scalars(
            select(Contract)
            .where(
                public_contract_filter(Contract),
                Contract.source_id == "sicoes",
                (Contract.contract_date.is_(None))
                | (func.extract("year", Contract.contract_date) >= year_from),
            )
            .order_by(Contract.contract_date.desc().nullslast())
            .limit(20000)
        ).all()
    )
    out_flags, gate = flag_counts(rows)
    sample_size = len(rows)
    gate_pass = sample_size == 0 or all(gate.values())

    known = list(
        db.scalars(
            select(Contract)
            .where(
                public_contract_filter(Contract),
                (Contract.amount.is_not(None) & (Contract.amount > 0))
                | Contract.has_awarded_amount.is_(True),
            )
            .limit(5000)
        ).all()
    )
    known_flags, _ = flag_counts(known)

    return SicoesCoverageOut(
        sample_size=sample_size,
        flags=out_flags,
        gate_pass=gate_pass,
        thresholds={"has_awarded_amount_or_ref": 0.40, "has_supplier": 0.30},
        known_amount_universe=len(known),
        known_amount_flags=known_flags,
    )
