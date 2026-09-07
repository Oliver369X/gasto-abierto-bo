"""F4: reclassify offline SICOES rows without promoting keyword evidence."""
from __future__ import annotations

from sqlalchemy import select

from common.fire.classify import classify_fire_text
from common.fire.ledger import amount_for_public_kpi
from schema.models import FireAttribution, FireCycle, FireExpenditure
from worker.fire.artifacts import write_json
from worker.fire.context import get_session


def reclassification_values(row: FireExpenditure) -> tuple:
    result = classify_fire_text(
        object_description=row.object_description,
        title=row.title,
    )
    bucket = {
        "directo": "probable",
        "probable": "probable",
        "parcial": "parcial",
        "indirecto": "indirecto",
        "no_relacionado": "no_relacionado",
    }[result.attribution]
    return result, bucket


def run(session=None, *, write_artifact: bool = True) -> dict:
    own = session is None
    session = session or get_session()
    try:
        all_rows = list(session.scalars(select(FireExpenditure)).all())
        kpi_before = sum(
            (amount_for_public_kpi(row) for row in all_rows if row.year == 2024),
            start=0,
        )
        rows = list(session.scalars(select(FireExpenditure).where(
            FireExpenditure.source_id == "sicoes_offline",
            FireExpenditure.is_synthetic.is_(False),
        )).all())
        counts: dict[str, int] = {}
        for row in rows:
            result, bucket = reclassification_values(row)
            row.attribution = FireAttribution(result.attribution)
            row.cycle = FireCycle(result.cycle)
            row.confidence_score = result.confidence_score
            row.classification_method = result.classification_method
            row.ledger_bucket = bucket  # keyword-only evidence is never verifiable
            row.evidence = {
                **(row.evidence or {}),
                "f04_reclassified": True,
                "matched_terms": result.matched_terms,
                "rules_fired": list(result.rules_fired),
            }
            counts[result.attribution] = counts.get(result.attribution, 0) + 1
        session.flush()
        kpi_after = sum(
            (amount_for_public_kpi(row) for row in all_rows if row.year == 2024),
            start=0,
        )
        session.commit()
        payload = {
            "status": "ok",
            "updated": len(rows),
            "by_attribution": counts,
            "verifiable_promotions": 0,
            "kpi_before": str(kpi_before),
            "kpi_after": str(kpi_after),
            "kpi_870k_preserved": kpi_before == kpi_after == 870000,
        }
        if write_artifact:
            write_json("f04_reclassify.json", payload)
        return payload
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()
