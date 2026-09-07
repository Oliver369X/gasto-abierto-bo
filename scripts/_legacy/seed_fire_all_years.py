#!/usr/bin/env python3
"""
Seed multi-gestión AURA Incendios from data/extracted/fire_all_years_db.json.
Loads DGF-SIMB hectares 2000-2025 + MINDEF ops/money 2022-2026 + discrepancies.
"""
from __future__ import annotations

import json
import os
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(ROOT / "services"))

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from schema.db import make_engine
from schema.models import (
    Discrepancy,
    DonationAid,
    FireAttribution,
    FireCycle,
    FireExpenditure,
    FireSeason,
    OperationalOutput,
)
from worker.persist import finish_run, get_or_create_entity, start_run
from worker.persist_fire import get_or_create_season, get_or_create_territory

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://gasto:gasto_dev_change_me@localhost:5434/gasto_abierto",
)
DB_PATH = ROOT / "data" / "extracted" / "fire_all_years_db.json"


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"Missing {DB_PATH} — run scripts/build_fire_all_years_db.py first")

    data = json.loads(DB_PATH.read_text(encoding="utf-8"))
    engine = make_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    n_ops = n_exp = n_disc = 0
    try:
        run = start_run(session, "seed_fire_all_years", meta={"source": str(DB_PATH.name)})
        bolivia = get_or_create_territory(session, "Bolivia", level="pais", slug="bolivia")
        mindef = get_or_create_entity(
            session, "Ministerio de Defensa", level="nacional", source_id="mindef_rpc_real", run_id=run.id
        )

        seasons: dict[int, FireSeason] = {}
        for s in data.get("seasons", []):
            seasons[s["year"]] = get_or_create_season(
                session,
                s["year"],
                quality_grade=s.get("quality_grade") or "B",
                notes=s.get("notes"),
            )
            # upgrade existing
            seasons[s["year"]].quality_grade = s.get("quality_grade") or seasons[s["year"]].quality_grade
            if s.get("notes"):
                seasons[s["year"]].notes = s["notes"]

        # Ensure seasons for hectare-only years
        for year in data.get("hectares_dgf_simb", {}):
            y = int(year)
            if y not in seasons:
                seasons[y] = get_or_create_season(
                    session,
                    y,
                    quality_grade="A" if y >= 2019 else "B",
                    notes=f"Serie DGF-SIMB hectáreas (Plan Prevención IF 2026)",
                )

        # Operational outputs — upsert by year+metric_key+source
        for op in data.get("operations", []):
            year = int(op["year"])
            key = op["metric_key"]
            src = op.get("source_id") or "mindef_rpc_real"
            existing = session.scalars(
                select(OperationalOutput).where(
                    OperationalOutput.year == year,
                    OperationalOutput.metric_key == key,
                    OperationalOutput.source_id == src,
                )
            ).first()
            if existing:
                existing.value_numeric = Decimal(str(op["value_numeric"]))
                existing.evidence_page = op.get("evidence_page")
                existing.evidence_quote = op.get("evidence_quote")
                existing.metric_label = op.get("metric_label")
                existing.unit = op.get("unit")
                continue
            session.add(
                OperationalOutput(
                    year=year,
                    metric_key=key,
                    metric_label=op.get("metric_label") or key,
                    value_numeric=Decimal(str(op["value_numeric"])),
                    unit=op.get("unit"),
                    evidence_page=op.get("evidence_page"),
                    evidence_quote=op.get("evidence_quote"),
                    source_id=src,
                )
            )
            n_ops += 1

        for cand in data.get("expenditure_candidates", []):
            code = cand["code"]
            if session.scalars(select(FireExpenditure).where(FireExpenditure.code == code)).first():
                continue
            year = int(cand["year"])
            season = seasons.get(year) or get_or_create_season(session, year)
            amt = cand.get("amount_bob")
            attributed = cand.get("amount_attributed_bob")
            session.add(
                FireExpenditure(
                    code=code,
                    year=year,
                    season_id=season.id,
                    title=cand["title"],
                    object_description=cand.get("evidence_quote") or cand["title"],
                    attribution=FireAttribution(cand["attribution"]),
                    confidence_score=Decimal("0.950")
                    if cand["attribution"] == "directo"
                    else Decimal("0.700"),
                    classification_method="pdf_official_quote",
                    cycle=FireCycle(cand.get("cycle") or "respuesta"),
                    paying_entity_id=mindef.id,
                    beneficiary_territory_id=bolivia.id,
                    amount_contract=Decimal(str(amt)) if amt is not None else None,
                    amount_attributed=Decimal(str(attributed)) if attributed is not None else None,
                    quality_grade=cand.get("quality_grade") or "A",
                    evidence={
                        "page": cand.get("evidence_page"),
                        "quote": cand.get("evidence_quote"),
                        "sha256": cand.get("source_document_sha256"),
                        "url": cand.get("source_url"),
                    },
                    source_id=cand.get("source_id") or "mindef_rpc_real",
                )
            )
            n_exp += 1

        for disc in data.get("discrepancies", []):
            concept = disc["concept"]
            row = session.scalars(select(Discrepancy).where(Discrepancy.concept == concept)).first()
            if row:
                row.amount_a = Decimal(str(disc["amount_a"]))
                row.amount_b = Decimal(str(disc["amount_b"]))
                row.source_a = disc.get("source_a")
                row.source_b = disc.get("source_b")
                row.ref_a = disc.get("ref_a")
                row.ref_b = disc.get("ref_b")
            else:
                session.add(
                    Discrepancy(
                        concept=concept,
                        amount_a=Decimal(str(disc["amount_a"])),
                        amount_b=Decimal(str(disc["amount_b"])),
                        source_a=disc.get("source_a"),
                        source_b=disc.get("source_b"),
                        ref_a=disc.get("ref_a"),
                        ref_b=disc.get("ref_b"),
                    )
                )
                n_disc += 1

        # Chile donation 2024 if missing
        if not session.scalars(
            select(DonationAid).where(DonationAid.donor_name.ilike("%Chile%incendios%"))
        ).first():
            session.add(
                DonationAid(
                    year=2024,
                    donor_name="Estado Plurinacional de Bolivia → Chile (incendios)",
                    description="Bs 870.000 logística donaciones incendios (MINDEF RPC 2024)",
                    amount=Decimal("870000"),
                    currency="BOB",
                    in_kind=True,
                    territory_id=bolivia.id,
                    evidence={
                        "page": 28,
                        "quote": "INCENDIOS FORESTALES ... Bs. 870.000",
                        "source": "mindef_rpc_final_2024",
                    },
                    source_id="mindef_rpc_real",
                )
            )

        finish_run(session, run, status="ok", records_in=n_ops + n_exp + n_disc, records_out=n_ops + n_exp)
        session.commit()
        print(f"OK ops+={n_ops} exp+={n_exp} disc+={n_disc}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
