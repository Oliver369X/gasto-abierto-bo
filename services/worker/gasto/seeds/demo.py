#!/usr/bin/env python3
"""Seed demo data without network. Idempotent-ish."""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(ROOT / "services"))

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from common.fuzzy import canonicalize_name
from schema.db import make_engine
from schema.models import AdminLevel, Alert, Contract, Entity, IngestionRun, Supplier
from worker.alerts import run_alert_rules
from worker.pipeline import run_ingest
from worker.persist import finish_run, start_run

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://gasto:gasto_dev_change_me@localhost:5434/gasto_abierto",
)
FIXTURES = ROOT / "tests" / "fixtures"


def main() -> None:
    engine = make_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        existing = session.scalars(select(Entity).limit(1)).first()
        if existing:
            if not session.scalars(select(Alert).limit(1)).first():
                run_alert_rules(session)
                session.commit()
            print("Seed skipped (data present)")
            return

        run = start_run(session, "seed", meta={"kind": "demo"})
        gam = Entity(
            name="GAM Santa Cruz de la Sierra",
            canonical_name=canonicalize_name("GAM Santa Cruz de la Sierra"),
            level=AdminLevel.municipal,
            department="Santa Cruz",
            source_id="seed",
            ingestion_run_id=run.id,
        )
        min_edu = Entity(
            name="Ministerio de Educación",
            canonical_name=canonicalize_name("Ministerio de Educación"),
            level=AdminLevel.nacional,
            source_id="seed",
            ingestion_run_id=run.id,
        )
        session.add_all([gam, min_edu])
        session.flush()

        sup = Supplier(
            name="Constructora Andes S.R.L.",
            canonical_name=canonicalize_name("Constructora Andes S.R.L."),
            nit="123456789",
            source_id="seed",
            ingestion_run_id=run.id,
        )
        session.add(sup)
        session.flush()

        now = datetime.now(timezone.utc)
        base = date(2026, 3, 10)
        for i, (amt, modality, days, obj) in enumerate(
            [
                (Decimal("1200000.00"), "Licitación Pública", 0, "Construcción de aula escolar"),
                (Decimal("800000.00"), "Adjudicación Directa", 5, "Mantenimiento vial emergencia"),
                (Decimal("200000.00"), "Adjudicación Directa", 12, "Servicio de vigilancia"),
                (Decimal("150000.00"), "Adjudicación Directa", 18, "Reparación de cordones A"),
                (Decimal("160000.00"), "Adjudicación Directa", 25, "Reparación de cordones B"),
            ],
            start=1,
        ):
            session.add(
                Contract(
                    cuce=f"26-0001-00-{i:06d}-1-1",
                    entity_id=gam.id,
                    supplier_id=sup.id,
                    object_description=obj,
                    modality=modality,
                    amount=amt,
                    contract_date=date.fromordinal(base.toordinal() + days),
                    status="Adjudicado",
                    source_id="seed",
                    ingestion_run_id=run.id,
                    valid_from=now,
                    is_current=True,
                )
            )

        from schema.models import AuditReport, BudgetLine

        session.add_all(
            [
                BudgetLine(
                    entity_id=min_edu.id,
                    year=2025,
                    program_project="Construcción de hospitales",
                    budget_item="2.01.01.01.01",
                    initial_amount=Decimal("50000000"),
                    modified_amount=Decimal("52000000"),
                    current_amount=Decimal("51000000"),
                    executed_amount=Decimal("25000000"),
                    source_id="seed",
                    ingestion_run_id=run.id,
                    valid_from=now,
                    is_current=True,
                ),
                BudgetLine(
                    entity_id=gam.id,
                    year=2025,
                    program_project="POA Municipal",
                    initial_amount=Decimal("4462105229"),
                    current_amount=Decimal("4453678601"),
                    executed_amount=Decimal("0"),
                    source_id="seed",
                    ingestion_run_id=run.id,
                    valid_from=now,
                    is_current=True,
                ),
                AuditReport(
                    entity_id=gam.id,
                    title="Informe de auditoría especial — GAM Santa Cruz (demo)",
                    year=2024,
                    url="https://www.contraloria.gob.bo/",
                    findings_summary="Hallazgos demo para UI.",
                    source_id="seed",
                    ingestion_run_id=run.id,
                ),
            ]
        )
        finish_run(session, run, status="ok", records_in=1, records_out=8)
        session.commit()

        fixture_map = {
            "agetic": "sample_contracts.csv",
            "sicoes": "procesos_sample.html",
            "presupuesto_abierto": "entidades.json",
            "cge": "informes_sample.html",
            "gad_scz": "portal_sample.html",
            "gam_scz": "rendicion_text.txt",
        }
        from worker.gasto.seeds._helpers import seed_skip_storage

        skip_storage = seed_skip_storage()
        for source_id, fname in fixture_map.items():
            path = FIXTURES / source_id / fname
            if not path.exists():
                continue
            run_ingest(
                session,
                source_id,
                fixture_path=str(path),
                skip_storage=skip_storage,
                skip_alerts=True,
            )
            session.commit()

        print("Seed OK")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
