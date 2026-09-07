"""F1: purge synthetic or unverified fire-ledger amounts."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from schema.models import FireExpenditure
from worker.fire.artifacts import write_json
from worker.fire.context import get_session

SYNTHETIC_CODES = {f"FIRE-BO-2024-{number:06d}" for number in range(1, 5)}


def _bucket_for(row: FireExpenditure) -> str:
    if row.is_synthetic or (row.quality_grade or "").upper() == "E":
        return "sintetico"
    attr = row.attribution.value if hasattr(row.attribution, "value") else str(row.attribution)
    return attr if attr in {"parcial", "probable", "indirecto", "no_relacionado"} else "probable"


def run(session=None, *, write_artifact: bool = True) -> dict:
    own = session is None
    session = session or get_session()
    try:
        rows = list(session.scalars(select(FireExpenditure)).all())
        synthetic = 0
        for row in rows:
            evidence = dict(row.evidence or {})
            grade = (row.quality_grade or "").upper()
            is_synthetic = (
                bool(evidence.get("is_synthetic"))
                or row.code in SYNTHETIC_CODES
                or (row.source_id == "seed_fire" and grade in {"C", "D", "E"})
            )
            row.is_synthetic = is_synthetic
            attr = row.attribution.value if hasattr(row.attribution, "value") else str(row.attribution)
            if is_synthetic:
                synthetic += 1
                row.ledger_bucket, row.allocation_method = "sintetico", "synthetic"
                row.allocation_confidence = Decimal("0")
                row.amount_attributed = row.amount_attributed_low = None
                row.amount_attributed_base = row.amount_attributed_high = None
                row.amount_total = row.amount_contract
                row.evidence = {**evidence, "is_synthetic": True, "f1_purged": True}
            elif attr == "directo" and grade == "A" and row.amount_attributed:
                row.ledger_bucket, row.allocation_method = "verificable", "exact"
                row.allocation_confidence = Decimal("0.950")
                row.amount_attributed_low = row.amount_attributed
                row.amount_attributed_base = row.amount_attributed
                row.amount_attributed_high = row.amount_attributed
                row.amount_total = row.amount_contract or row.amount_attributed
            else:
                row.ledger_bucket = _bucket_for(row)
                row.amount_total = row.amount_contract or row.amount_attributed
        session.commit()
        verifiable = [row for row in rows if row.ledger_bucket == "verificable"]
        payload = {
            "status": "ok",
            "rows_processed": len(rows),
            "synthetic_purged": synthetic,
            "verifiable_count": len(verifiable),
            "verifiable_sum": str(sum((r.amount_attributed or Decimal("0")) for r in verifiable)),
        }
        if write_artifact:
            write_json("f1_purge.json", payload)
        return payload
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()
