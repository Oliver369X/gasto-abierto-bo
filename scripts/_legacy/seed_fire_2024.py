#!/usr/bin/env python3
"""Seed / expand AURA Incendios: multi-año + gaceta + SERNAP + FIRMS + alertas."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(ROOT / "services"))

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from common.fire.classify import classify_fire_text
from common.fuzzy import canonicalize_name
from schema.db import make_engine
from schema.models import (
    ActiveFireDetection,
    Contract,
    Discrepancy,
    Document,
    DonationAid,
    EmergencyDeclaration,
    FireAttribution,
    FireCycle,
    FireExpenditure,
    FireSeason,
)
from worker.adapters.abt import AbtAdapter
from worker.adapters.base import Cursor, StagingRecord
from worker.adapters.firms import FirmsAdapter
from worker.adapters.gaceta_scz import GacetaSczAdapter
from worker.adapters.mindef import MindefAdapter
from worker.adapters.sernap import SernapAdapter
from worker.alerts_fire import run_fire_alert_rules
from worker.persist import finish_run, get_or_create_entity, get_or_create_supplier, persist_staging, start_run
from worker.persist_fire import get_or_create_season, get_or_create_territory, persist_fire_staging

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://gasto:gasto_dev_change_me@127.0.0.1:5434/gasto_abierto",  # pragma: allowlist secret
)
FIXTURES = ROOT / "tests" / "fixtures"
REAL_DB = ROOT / "data" / "extracted" / "fire_real_db.json"

AIRCRAFT = [
    {
        "code": "FIRE-BO-2024-000001",
        "cuce": "24-FIRE-AERO-000001-1-1",
        "title": "Alquiler de aeronave para lucha contra incendios forestales",
        "supplier": "AeroServicios Andinos S.A.",
        "nit": "102938475",
        "amount": Decimal("12500000.00"),
        "territory": "Santa Cruz",
    },
    {
        "code": "FIRE-BO-2024-000002",
        "cuce": "24-FIRE-AERO-000002-1-1",
        "title": "Alquiler de helicóptero con Bambi Bucket para combate de incendios forestales",
        "supplier": "Helicópteros del Oriente Ltda.",
        "nit": "198765432",
        "amount": Decimal("9800000.00"),
        "territory": "Santa Cruz",
    },
    {
        "code": "FIRE-BO-2024-000003",
        "cuce": "24-FIRE-AERO-000003-1-1",
        "title": "Alquiler de avión cisterna para descarga de agua en incendios forestales",
        "supplier": "SkyTank Bolivia S.R.L.",
        "nit": "156789012",
        "amount": Decimal("15200000.00"),
        "territory": "Beni",
    },
    {
        "code": "FIRE-BO-2024-000004",
        "cuce": "24-FIRE-AERO-000004-1-1",
        "title": "Alquiler de aeronave Sistema Guardian para operaciones aéreas contra incendios",
        "supplier": "Guardian Air Ops S.A.",
        "nit": "167890123",
        "amount": Decimal("11000000.00"),
        "territory": "Santa Cruz",
    },
]

EXTRA_EXPENDITURES = [
    {
        "code": "FIRE-BO-2023-000001",
        "year": 2023,
        "title": "Combustible para maquinaria pesada — emergencia incendios San Matías",
        "amount": Decimal("1850000.00"),
        "attribution": "probable",
        "cycle": "respuesta",
        "territory": "Santa Cruz",
        "quality": "C",
        "entity": "Gobierno Autónomo Departamental de Santa Cruz",
        "level": "departamental",
    },
    {
        "code": "FIRE-BO-2023-000002",
        "year": 2023,
        "title": "Monitoreo de focos de calor y brigadas preventivas ABT",
        "amount": Decimal("2100000.00"),
        "attribution": "directo",
        "cycle": "prevencion",
        "territory": "Santa Cruz",
        "quality": "B",
        "entity": "Autoridad de Fiscalización y Control Social de Bosques y Tierra",
        "level": "nacional",
    },
    {
        "code": "FIRE-BO-2022-000001",
        "year": 2022,
        "title": "Adquisición de equipos contra incendios forestales — brigadas",
        "amount": Decimal("3200000.00"),
        "attribution": "directo",
        "cycle": "preparacion",
        "territory": "Beni",
        "quality": "C",
        "entity": "Ministerio de Defensa",
        "level": "nacional",
    },
    {
        "code": "FIRE-BO-2025-000001",
        "year": 2025,
        "title": "Alquiler de aeronave para lucha contra incendios forestales — temporada 2025",
        "amount": Decimal("14000000.00"),
        "attribution": "directo",
        "cycle": "respuesta",
        "territory": "Santa Cruz",
        "quality": "D",
        "entity": "Ministerio de Defensa",
        "level": "nacional",
    },
    {
        "code": "FIRE-BO-2024-000010",
        "year": 2024,
        "title": "Reforestación post-incendio en municipios afectados",
        "amount": Decimal("4500000.00"),
        "attribution": "directo",
        "cycle": "recuperacion",
        "territory": "Santa Cruz",
        "quality": "C",
        "entity": "Autoridad de Fiscalización y Control Social de Bosques y Tierra",
        "level": "nacional",
    },
    {
        "code": "FIRE-BO-2024-000011",
        "year": 2024,
        "title": "Víveres y alimentación de brigadistas forestales",
        "amount": Decimal("890000.00"),
        "attribution": "probable",
        "cycle": "respuesta",
        "territory": "Beni",
        "quality": "C",
        "entity": "Ministerio de Defensa",
        "level": "nacional",
    },
    {
        "code": "FIRE-BO-2024-000020",
        "year": 2024,
        "title": "Combustible y maquinaria para sofocación — municipio Concepción",
        "amount": Decimal("1250000.00"),
        "attribution": "directo",
        "cycle": "respuesta",
        "territory": "Concepción",
        "territory_level": "municipio",
        "parent_dept": "Santa Cruz",
        "quality": "C",
        "entity": "Gobierno Autónomo Municipal de Concepción",
        "level": "municipal",
    },
    {
        "code": "FIRE-BO-2024-000021",
        "year": 2024,
        "title": "Brigadas forestales municipales — San Ignacio de Velasco",
        "amount": Decimal("980000.00"),
        "attribution": "directo",
        "cycle": "respuesta",
        "territory": "San Ignacio de Velasco",
        "territory_level": "municipio",
        "parent_dept": "Santa Cruz",
        "quality": "C",
        "entity": "Gobierno Autónomo Municipal de San Ignacio de Velasco",
        "level": "municipal",
    },
    {
        "code": "FIRE-BO-2024-000022",
        "year": 2024,
        "title": "Combustible para maquinaria pesada durante emergencia incendios — San Matías",
        "amount": Decimal("2100000.00"),
        "attribution": "probable",
        "cycle": "respuesta",
        "territory": "San Matías",
        "territory_level": "municipio",
        "parent_dept": "Santa Cruz",
        "quality": "C",
        "entity": "Gobierno Autónomo Municipal de San Matías",
        "level": "municipal",
    },
    {
        "code": "FIRE-BO-2024-000023",
        "year": 2024,
        "title": "Cortafuegos preventivos y monitoreo de focos de calor — Roboré",
        "amount": Decimal("640000.00"),
        "attribution": "directo",
        "cycle": "prevencion",
        "territory": "Roboré",
        "territory_level": "municipio",
        "parent_dept": "Santa Cruz",
        "quality": "B",
        "entity": "Gobierno Autónomo Municipal de Roboré",
        "level": "municipal",
    },
]


def _ingest_adapter(session, run, adapter_cls, fixture_rel: str) -> int:
    path = FIXTURES / fixture_rel
    if not path.exists():
        print(f"skip missing fixture {path}")
        return 0
    adapter = adapter_cls()
    items = adapter.discover(Cursor(payload={"fixture_path": str(path)}))
    raw = adapter.fetch(items[0])
    records = adapter.parse(raw)
    generic = [r for r in records if r.record_type in ("budget", "contract", "audit", "document")]
    fire = [r for r in records if r.record_type not in ("budget", "contract", "audit")]
    n = 0
    if generic:
        n += persist_staging(session, generic, source_id=adapter.source_id, run=run)
    if fire:
        n += persist_fire_staging(session, fire, source_id=adapter.source_id, run=run)
    return n


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    engine = make_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        run = start_run(session, "seed_fire", meta={"kind": "fire_expand", "force": args.force})

        bolivia = get_or_create_territory(session, "Bolivia", level="pais", slug="bolivia")
        depts = {}
        for name in (
            "Santa Cruz", "Beni", "Pando", "La Paz", "Cochabamba",
            "Chuquisaca", "Tarija", "Oruro", "Potosí",
        ):
            slug = canonicalize_name(name).replace(" ", "-")
            depts[name] = get_or_create_territory(
                session, name, level="departamento", parent_id=bolivia.id, slug=slug
            )

        # Municipios prioritarios Santa Cruz (afectados históricamente)
        munis = {}
        for muni in (
            "Concepción",
            "San Ignacio de Velasco",
            "San Matías",
            "Roboré",
            "San José de Chiquitos",
            "Puerto Suárez",
        ):
            slug = canonicalize_name(muni).replace(" ", "-")
            munis[muni] = get_or_create_territory(
                session,
                muni,
                level="municipio",
                parent_id=depts["Santa Cruz"].id,
                slug=slug,
            )

        seasons = {}
        for year, start, end, grade, notes in [
            (2022, date(2022, 6, 1), date(2022, 11, 30), "E", "Archivo histórico — cobertura parcial"),
            (2023, date(2023, 6, 1), date(2023, 11, 30), "C", "Serie intermedia ABT + contratos"),
            (
                2024,
                date(2024, 6, 3),
                date(2024, 11, 5),
                "B",
                "Ops VIDECI calidad A (RPC PDF sha real); montos aeronaves SICOES aún E/sintéticos",
            ),
            (2025, date(2025, 6, 1), date(2025, 11, 30), "E", "Temporada parcial"),
        ]:
            seasons[year] = get_or_create_season(
                session, year, start_date=start, end_date=end, quality_grade=grade, notes=notes
            )
        # Upgrade existing 2024 season notes/grade if already present
        s24 = seasons[2024]
        s24.quality_grade = "B"
        s24.notes = (
            "Ops VIDECI calidad A (RPC PDF sha real); montos aeronaves SICOES aún E/sintéticos"
        )

        n = 0
        core = session.scalars(
            select(FireExpenditure).where(FireExpenditure.code == "FIRE-BO-2024-000001")
        ).first()

        if not core:
            n += _ingest_adapter(session, run, MindefAdapter, "mindef/rpc_2024.json")
            aero = json.loads((FIXTURES / "sicoes/fire_2024/aeronaves.json").read_text(encoding="utf-8"))
            persist_staging(
                session,
                [StagingRecord(record_type="contract", data=row) for row in aero["records"]],
                source_id="sicoes",
                run=run,
            )
            session.flush()
            mindef = get_or_create_entity(
                session, "Ministerio de Defensa", level="nacional", source_id="seed_fire", run_id=run.id
            )
            doc = session.scalars(select(Document).where(Document.source_id == "mindef").limit(1)).first()
            for item in AIRCRAFT:
                supplier = get_or_create_supplier(
                    session, item["supplier"], nit=item["nit"], source_id="seed_fire", run_id=run.id
                )
                contract = session.scalars(
                    select(Contract).where(Contract.cuce == item["cuce"], Contract.is_current.is_(True))
                ).first()
                session.add(
                    FireExpenditure(
                        code=item["code"],
                        year=2024,
                        season_id=seasons[2024].id,
                        title=item["title"],
                        object_description=item["title"],
                        attribution=FireAttribution.directo,
                        confidence_score=Decimal("0.400"),
                        classification_method="document_link",
                        cycle=FireCycle.respuesta,
                        paying_entity_id=mindef.id,
                        beneficiary_territory_id=depts[item["territory"]].id,
                        supplier_id=supplier.id if supplier else None,
                        contract_id=contract.id if contract else None,
                        document_id=doc.id if doc else None,
                        amount_contract=item["amount"],
                        amount_attributed=None,  # no sumar montos sintéticos al ledger verificable
                        quality_grade="E",
                        cuce=item["cuce"],
                        evidence={
                            "url": "https://www.mindef.gob.bo/wp-content/uploads/2026/01/12032025_INFORME_RPCFinal_2024_V15.pdf",
                            "page": 28,
                            "quote": "4 Procesos de Contratación de Alquiler Aeronaves Para Lucha Contra Incendios concluidos",
                            "is_synthetic": True,
                            "note": "Proceso confirmado por MINDEF; monto/CUCE/proveedor sintéticos hasta SICOES live",
                        },
                        source_id="seed_fire",
                    )
                )
                n += 1
            n += _ingest_adapter(session, run, AbtAdapter, "abt/ejecucion_2024.json")
            print("Core 2024 aircraft seed created (quality E synthetic amounts)")
        else:
            print("Core 2024 present — expanding")
            # Demote any prior synthetic aircraft rows still marked D
            for row in session.scalars(
                select(FireExpenditure).where(
                    FireExpenditure.code.in_([a["code"] for a in AIRCRAFT])
                )
            ):
                row.quality_grade = "E"
                row.amount_attributed = None
                row.confidence_score = Decimal("0.400")
                ev = dict(row.evidence or {})
                ev["is_synthetic"] = True
                ev["note"] = (
                    "Proceso confirmado por MINDEF; monto/CUCE/proveedor sintéticos hasta SICOES live"
                )
                row.evidence = ev

        for item in EXTRA_EXPENDITURES:
            if session.scalars(select(FireExpenditure).where(FireExpenditure.code == item["code"])).first():
                continue
            ent = get_or_create_entity(
                session,
                item["entity"],
                level=item.get("level") or "nacional",
                source_id="seed_fire",
                run_id=run.id,
                department=item.get("parent_dept") or item["territory"],
            )
            terr_name = item["territory"]
            if item.get("territory_level") == "municipio":
                if terr_name not in munis:
                    parent = depts.get(item.get("parent_dept") or "Santa Cruz")
                    slug = canonicalize_name(terr_name).replace(" ", "-")
                    munis[terr_name] = get_or_create_territory(
                        session,
                        terr_name,
                        level="municipio",
                        parent_id=parent.id if parent else None,
                        slug=slug,
                    )
                terr_id = munis[terr_name].id
            else:
                terr_id = depts[terr_name].id
            session.add(
                FireExpenditure(
                    code=item["code"],
                    year=item["year"],
                    season_id=seasons[item["year"]].id,
                    title=item["title"],
                    object_description=item["title"],
                    attribution=FireAttribution(item["attribution"]),
                    confidence_score=(
                        Decimal("0.850") if item["attribution"] == "probable" else Decimal("0.950")
                    ),
                    classification_method="exact_keyword",
                    cycle=FireCycle(item["cycle"]),
                    paying_entity_id=ent.id,
                    beneficiary_territory_id=terr_id,
                    amount_contract=item["amount"],
                    amount_attributed=item["amount"],
                    quality_grade=item["quality"],
                    evidence={
                        "note": "Seed multi-año / municipal",
                        "matched_terms": classify_fire_text(
                            object_description=item["title"]
                        ).matched_terms,
                    },
                    source_id="seed_fire",
                )
            )
            n += 1

        decl_n = session.scalar(select(func.count()).select_from(EmergencyDeclaration)) or 0
        firms_n = session.scalar(select(func.count()).select_from(ActiveFireDetection)) or 0
        if args.force or decl_n < 2:
            n += _ingest_adapter(session, run, GacetaSczAdapter, "gaceta_scz/decretos_incendio.json")
        n += _ingest_adapter(session, run, SernapAdapter, "sernap/incendios_ap.json")
        if args.force or firms_n < 5:
            n += _ingest_adapter(session, run, FirmsAdapter, "firms/bolivia_2024_sample.json")

        # --- Real PDF candidates (MINDEF RPC 2024) ---
        if REAL_DB.exists():
            real = json.loads(REAL_DB.read_text(encoding="utf-8"))
            mindef_ent = get_or_create_entity(
                session, "Ministerio de Defensa", level="nacional", source_id="seed_fire", run_id=run.id
            )
            for cand in real.get("mindef_rpc_2024", {}).get("money_and_budget", []):
                if cand.get("record_type") != "fire_expenditure_candidate":
                    continue
                code = cand["code"]
                if session.scalars(select(FireExpenditure).where(FireExpenditure.code == code)).first():
                    continue
                amt = cand.get("amount_bob")
                attr = cand.get("attribution", "no_relacionado")
                attributed = None
                if attr == "directo" and amt is not None:
                    attributed = Decimal(str(amt))
                session.add(
                    FireExpenditure(
                        code=code,
                        year=int(cand["year"]),
                        season_id=seasons[int(cand["year"])].id,
                        title=cand["title"],
                        object_description=cand.get("attribution_reason") or cand["title"],
                        attribution=FireAttribution(attr),
                        confidence_score=(
                            Decimal("0.950") if attr == "directo" else Decimal("0.700")
                        ),
                        classification_method="pdf_official_quote",
                        cycle=FireCycle(cand.get("cycle") or "respuesta"),
                        paying_entity_id=mindef_ent.id,
                        beneficiary_territory_id=bolivia.id,
                        amount_contract=Decimal(str(amt)) if amt is not None else None,
                        amount_attributed=attributed,
                        quality_grade=cand.get("quality_grade") or "A",
                        evidence={
                            "url": cand.get("source_url"),
                            "page": cand.get("evidence_page"),
                            "quote": cand.get("evidence_quote"),
                            "sha256": cand.get("source_document_sha256"),
                            "attribution_reason": cand.get("attribution_reason"),
                        },
                        source_id="mindef_rpc_real",
                    )
                )
                n += 1
            # Refresh MINDEF operational metrics from updated fixture
            n += _ingest_adapter(session, run, MindefAdapter, "mindef/rpc_2024.json")
            print(f"Ingested real MINDEF PDF candidates from {REAL_DB.name}")

        if not session.scalars(
            select(DonationAid).where(DonationAid.donor_name.ilike("%Chile%incendios%"))
        ).first():
            session.add(
                DonationAid(
                    year=2024,
                    donor_name="Estado Plurinacional de Bolivia → Chile (incendios)",
                    description=(
                        "Logística y transporte de donaciones (leche, aceite, harina, medicamentos) "
                        "por incendios forestales — Bs 870.000 (MINDEF RPC 2024 p.28)"
                    ),
                    amount=Decimal("870000.00"),
                    currency="BOB",
                    in_kind=True,
                    territory_id=bolivia.id,
                    evidence={
                        "url": "https://www.mindef.gob.bo/wp-content/uploads/2026/01/12032025_INFORME_RPCFinal_2024_V15.pdf",
                        "page": 28,
                        "quote": "INCENDIOS FORESTALES ... presupuesto de Bs. 870.000",
                        "sha256": "86a38097ec9854c97386a1f7f5362c7b502c95720be9d5737c40929155809c14",
                        "direction": "outflow_bolivia_to_chile",
                    },
                    source_id="mindef_rpc_real",
                )
            )
        if not session.scalars(select(DonationAid).where(DonationAid.year == 2024)).first():
            session.add(
                DonationAid(
                    year=2024,
                    donor_name="Cooperación internacional (stub)",
                    description="Equipos en especie — placeholder",
                    in_kind=True,
                    territory_id=depts["Santa Cruz"].id,
                    evidence={"note": "Sin monto verificable"},
                    source_id="seed_fire",
                )
            )
        if not session.scalars(
            select(DonationAid).where(DonationAid.donor_name.ilike("%Brasil%"))
        ).first():
            session.add(
                DonationAid(
                    year=2024,
                    donor_name="Gobierno de Brasil — apoyo aéreo (anunciado)",
                    description="Ayuda anunciada — monto no verificable en docs bolivianos",
                    amount=Decimal("0"),
                    in_kind=True,
                    territory_id=depts["Santa Cruz"].id,
                    evidence={"note": "Anunciado ≠ ejecutado verificable"},
                    source_id="seed_fire",
                )
            )

        disc = session.scalars(
            select(Discrepancy).where(Discrepancy.concept == "fire:emergencia_pool_vs_atribuible:2024")
        ).first()
        if disc:
            disc.amount_a = Decimal("161578899.00")
            disc.amount_b = Decimal("870000.00")
            disc.source_a = "mindef_rpc_2024_pools_multi_evento"
            disc.source_b = "mindef_rpc_2024_donacion_chile_incendios"
            disc.ref_a = "Bs 18.8M+116M+9.9M+16.6M+2.8M (NO 100% incendio)"
            disc.ref_b = "Bs 870.000 donacion Chile incendios (calidad A)"
        else:
            session.add(
                Discrepancy(
                    concept="fire:emergencia_pool_vs_atribuible:2024",
                    amount_a=Decimal("161578899.00"),
                    amount_b=Decimal("870000.00"),
                    source_a="mindef_rpc_2024_pools_multi_evento",
                    source_b="mindef_rpc_2024_donacion_chile_incendios",
                    ref_a="Bs 18.8M+116M+9.9M+16.6M+2.8M (NO 100% incendio)",
                    ref_b="Bs 870.000 donacion Chile incendios (calidad A)",
                )
            )
        if not session.scalars(
            select(Discrepancy).where(Discrepancy.concept == "fire:hectareas_nacional_2024_fuentes")
        ).first():
            session.add(
                Discrepancy(
                    concept="fire:hectareas_nacional_2024_fuentes",
                    amount_a=Decimal("12600000.00"),
                    amount_b=Decimal("14000000.00"),
                    source_a="defensoria_pueblo_efe",
                    source_b="geomatica_sumando_voces",
                    ref_a="12,6 M ha",
                    ref_b="14 M ha (SCZ 9,15M + Beni 3,89M + …)",
                )
            )

        alerts = run_fire_alert_rules(session)
        finish_run(session, run, status="ok", records_in=n, records_out=n + len(alerts))
        session.commit()
        print(f"Fire expand OK - records~={n}, fire_alerts={len(alerts)}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
