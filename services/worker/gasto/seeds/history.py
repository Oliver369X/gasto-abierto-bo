#!/usr/bin/env python3
"""Load multi-year historical fixtures (2019–2025) into the DB.

Safe offline path — no live network. Batches commits by gestión to stay
within Docker memory limits (~512MB).

Host fallback when Docker RAM is low:

  LOW_DOCKER_RAM=1 ./scripts/host_seed_history.sh

Run inside Docker:

  docker compose run --rm api python -m scripts.cli gasto seed --profile history
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(ROOT / "services"))

from sqlalchemy.orm import sessionmaker

from schema.db import make_engine
from worker.adapters.base import StagingRecord
from worker.adapters.presupuesto_abierto import PresupuestoAbiertoAdapter
from worker.gasto.seeds._helpers import (
    seed_batch_size,
    seed_log,
    seed_skip_alerts_during_ingest,
    seed_skip_storage,
)
from worker.pipeline import run_ingest
from worker.persist import finish_run, persist_staging, start_run

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://gasto:gasto_dev_change_me@127.0.0.1:5434/gasto_abierto",  # pragma: allowlist secret
)
FIXTURES = ROOT / "tests" / "fixtures"


def load_presupuesto_history(session) -> int:
    path = FIXTURES / "presupuesto_abierto" / "history_2019_2025.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    adapter = PresupuestoAbiertoAdapter()
    series: list[dict] = data["series"]
    years = sorted({int(row["gestion"]) for row in series})
    batch_size = seed_batch_size(25)
    total = 0

    for year in years:
        year_rows = [row for row in series if int(row["gestion"]) == year]
        records: list[StagingRecord] = []
        for row in year_rows:
            payload = {
                "entidades": [
                    {
                        "entidad": row["entidad"],
                        "nivel": row["nivel"],
                        "gestion": row["gestion"],
                        "departamento": row.get("departamento"),
                        "presupuesto_inicial": row["presupuesto_inicial"],
                        "presupuesto_vigente": row["presupuesto_vigente"],
                        "ejecucion": row["ejecucion"],
                    }
                ]
            }
            records.extend(adapter.parse(json.dumps(payload).encode("utf-8")))

        for chunk_idx, chunk in enumerate(
            [records[i : i + batch_size] for i in range(0, len(records), batch_size)]
        ):
            run = start_run(
                session,
                "presupuesto_abierto",
                meta={"kind": "history_2019_2025", "year": year, "chunk": chunk_idx},
            )
            n = persist_staging(session, chunk, source_id="presupuesto_abierto", run=run)
            finish_run(session, run, status="ok", records_in=len(chunk), records_out=n)
            session.commit()
            total += n
            seed_log("presupuesto_history", f"year={year} chunk={chunk_idx + 1} rows={n}")

    return total


def main() -> None:
    Session = sessionmaker(bind=make_engine(DATABASE_URL), autoflush=False, autocommit=False)
    session = Session()
    skip_storage = seed_skip_storage()
    skip_alerts = seed_skip_alerts_during_ingest()
    try:
        seed_log("history", "contracts CSV ingest")
        hist_csv = FIXTURES / "agetic" / "contracts_history_2019_2025.csv"
        result = run_ingest(
            session,
            "agetic",
            fixture_path=str(hist_csv),
            live=False,
            skip_storage=skip_storage,
            skip_alerts=skip_alerts,
        )
        session.commit()
        seed_log("history", f"contracts rows={result.get('records', 0)}")

        n = load_presupuesto_history(session)
        seed_log("history", f"presupuesto total rows={n}")

        seed_log("history", "backfill entity geo metadata")
        from common.entity_geo import infer_department, infer_entity_level
        from schema.models import AdminLevel, Entity
        from sqlalchemy import select

        level_map = {
            "nacional": AdminLevel.nacional,
            "departamental": AdminLevel.departamental,
            "municipal": AdminLevel.municipal,
        }
        for ent in session.scalars(select(Entity)).all():
            if not ent.department:
                inferred = infer_department(ent.name)
                if inferred:
                    ent.department = inferred
            inferred_level = infer_entity_level(ent.name)
            if inferred_level in level_map and ent.level == AdminLevel.nacional and inferred_level != "nacional":
                ent.level = level_map[inferred_level]
        session.commit()

        seed_log("history", "reconcile cross-source")
        from worker.reconcile import reconcile_all

        recon = reconcile_all(session)
        session.commit()
        seed_log("history", f"reconcile={recon}")

        from worker.alerts import run_alert_rules

        seed_log("history", "refreshing alerts")
        alerts = run_alert_rules(session)
        session.commit()
        seed_log("history", f"alerts={len(alerts)}")
        print("Seed history OK", flush=True)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
