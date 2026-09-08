from __future__ import annotations

import os
from pathlib import Path

from arq import cron
from arq.connections import RedisSettings
from sqlalchemy.orm import sessionmaker

from common.http_client import proxy_status, resolve_proxy_url
from schema.db import make_engine
from worker.pipeline import run_ingest

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://gasto:gasto_dev_change_me@localhost:5434/gasto_abierto",
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380/0")
ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"

DEFAULT_FIXTURES = {
    "agetic": "sample_contracts.csv",
    "sicoes": "procesos_sample.html",
    "presupuesto_abierto": "entidades.json",
    "cge": "informes_sample.html",
    "gad_scz": "portal_sample.html",
    "gam_scz": "rendicion_text.txt",
    "mindef": "rpc_2024.json",
    "abt": "ejecucion_2024.json",
    "gaceta_scz": "decretos_incendio.json",
    "sernap": "incendios_ap.json",
    "firms": "bolivia_2024_sample.json",
}


def _session():
    engine = make_engine(DATABASE_URL)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def _fixture_for(source_id: str) -> str | None:
    if os.getenv("LIVE_SCRAPE", "0") == "1":
        return None
    name = DEFAULT_FIXTURES.get(source_id)
    if not name:
        return None
    path = FIXTURES / source_id / name
    return str(path) if path.exists() else None


async def ingest_source(ctx, source_id: str, fixture_name: str | None = None) -> dict:
    fixture_path = None
    if fixture_name:
        fixture_path = str(FIXTURES / source_id / fixture_name)
    else:
        fixture_path = _fixture_for(source_id)

    session = _session()
    try:
        result = run_ingest(
            session,
            source_id,
            fixture_path=fixture_path,
            live=os.getenv("LIVE_SCRAPE", "0") == "1",
            max_pages=int(os.getenv("SICOES_MAX_PAGES", "25")),
        )
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def generate_alerts(ctx) -> dict:
    from worker.alerts import run_alert_rules
    from worker.alerts_fire import run_fire_alert_rules

    session = _session()
    try:
        alerts = run_alert_rules(session)
        fire_alerts = run_fire_alert_rules(session)
        session.commit()
        return {"alerts": len(alerts), "fire_alerts": len(fire_alerts)}
    finally:
        session.close()


async def classify_fire(ctx, year: int | None = 2024) -> dict:
    """Scan contracts and materialize fire_expenditure candidates."""
    from worker.persist_fire import classify_contracts_to_fire

    session = _session()
    try:
        run = classify_contracts_to_fire(session, year=year)
        session.commit()
        return {
            "status": run.status,
            "records_in": run.records_in,
            "records_out": run.records_out,
            "run_id": run.id,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def ingest_all_mvp(ctx) -> dict:
    results = []
    for source_id in DEFAULT_FIXTURES:
        results.append(await ingest_source(ctx, source_id))
    return {"sources": results}


async def ingest_sicoes_scheduled(ctx) -> dict:
    """Nightly SICOES ingest: live when proxy configured, else offline fixtures."""
    live = os.getenv("LIVE_SCRAPE", "0") == "1"
    proxy = resolve_proxy_url()
    require_proxy = os.getenv("REQUIRE_PROXY_FOR_LIVE", "1") == "1"
    mode = "fixture"
    if live and (proxy or not require_proxy):
        mode = "live"
    elif live and require_proxy and not proxy:
        mode = "fixture_no_proxy"
    result = await ingest_source(ctx, "sicoes")
    return {"mode": mode, "proxy": proxy_status(), "result": result}


async def ingest_presupuesto_scheduled(ctx) -> dict:
    """Weekly presupuesto refresh: live URLs when configured, else fixtures."""
    live = os.getenv("LIVE_SCRAPE", "0") == "1"
    proxy = resolve_proxy_url()
    require_proxy = os.getenv("REQUIRE_PROXY_FOR_LIVE", "1") == "1"
    mode = "fixture"
    if live and (proxy or not require_proxy):
        mode = "live"
    result = await ingest_source(ctx, "presupuesto_abierto")
    return {"mode": mode, "result": result}


class WorkerSettings:
    functions = [
        ingest_source,
        generate_alerts,
        ingest_all_mvp,
        classify_fire,
        ingest_sicoes_scheduled,
        ingest_presupuesto_scheduled,
    ]
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
    cron_jobs = [
        cron(generate_alerts, hour={6}, minute={0}),
        cron(ingest_all_mvp, hour={3}, minute={30}, weekday={0, 2, 4}),
        cron(ingest_sicoes_scheduled, hour={4}, minute={0}, weekday={1}),
        cron(ingest_presupuesto_scheduled, hour={4}, minute={30}, weekday={1}),
    ]
