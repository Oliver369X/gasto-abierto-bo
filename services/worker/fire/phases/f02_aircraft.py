"""F2: resolve the four documented MINDEF 2024 aircraft processes."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from schema.models import FireAttribution, FireCycle, FireExpenditure, FireLink
from worker.fire.artifacts import write_json
from worker.fire.context import finish_fire_run, get_session, start_fire_run
from worker.persist import get_or_create_entity
from worker.persist_fire import get_or_create_season, get_or_create_territory

KNOWN = [
    ("FIRE-BO-2024-AERO-01", "24-0020-00-1489620-0-E", "Servicio de alquiler de aeronave para la lucha de incendios forestales por emergencia nacional — 2024"),
    ("FIRE-BO-2024-AERO-02", "24-0020-00-1505677-0-E", "Servicio de alquiler de aeronave para la lucha de incendios forestales por desastre nacional — 2024"),
    ("FIRE-BO-2024-AERO-03", "24-0020-00-1483406-0-E", "Alquiler de helicóptero para la lucha de incendios forestales — Plan Nacional de Emergencias gestión 2024"),
    ("FIRE-BO-2024-AERO-04", None, "Proceso 4/4 de alquiler de aeronaves (confirmado MINDEF RPC 2024; CUCE no hallado en corpus offline)"),
]


def dossier_fields(code: str, cuce: str | None, title: str) -> dict:
    missing = "not_published" if cuce else "not_publicly_recoverable"
    return {"cuce": cuce or missing, "entity": "Ministerio de Defensa", "object": title,
            "modality": "EM" if cuce else missing, "date": missing,
            "precio_referencial": "not_published", "proveedor": missing, "nit": missing,
            "monto_adjudicado": missing, "contrato": missing, "documentos": missing,
            "periodo_operacional": "not_determinable",
            "territorio": "Bolivia (nacional)", "modificaciones": "not_published",
            "pagos": "not_published",
            "source": "sicoes_offline_corpus" if cuce else "mindef_rpc_2024_p28_only"}


def run(session=None, *, write_artifact: bool = True) -> dict:
    own = session is None
    session = session or get_session()
    dossiers = [{"code": c, "cuce": q, "title": t, "process_index": i,
                 "fields": dossier_fields(c, q, t)} for i, (c, q, t) in enumerate(KNOWN, 1)]
    try:
        job = start_fire_run(session, "f2_aeronaves")
        territory = get_or_create_territory(session, "Bolivia", level="pais", slug="bolivia")
        season = get_or_create_season(session, 2024, start_date=date(2024, 6, 3),
                                      end_date=date(2024, 11, 5), quality_grade="B")
        entity = get_or_create_entity(session, "Ministerio de Defensa", level="nacional",
                                      source_id="sicoes", run_id=job.id)
        for dossier in dossiers:
            row = session.scalars(select(FireExpenditure).where(
                FireExpenditure.code == dossier["code"])).first()
            evidence = {"f2_dossier": dossier["fields"], "process_index": dossier["process_index"],
                        "link_strength_ops": "FUERTEMENTE_VINCULADO"}
            if row is None:
                row = FireExpenditure(
                    code=dossier["code"], year=2024, season_id=season.id, title=dossier["title"],
                    object_description=dossier["title"], attribution=FireAttribution.directo,
                    confidence_score=Decimal("0.900" if dossier["cuce"] else "0.700"),
                    classification_method="sicoes_offline", cycle=FireCycle.respuesta,
                    paying_entity_id=entity.id, beneficiary_territory_id=territory.id,
                    allocation_method="none", allocation_confidence=Decimal("0"),
                    ledger_bucket="verificable" if dossier["cuce"] else "probable",
                    is_synthetic=False, recovery_status="amount_not_published" if dossier["cuce"] else "not_publicly_recoverable",
                    link_strength="FUERTEMENTE_VINCULADO", quality_grade="B" if dossier["cuce"] else "C",
                    cuce=dossier["cuce"], evidence=evidence, source_id="sicoes_offline")
                session.add(row)
            else:
                row.cuce, row.title, row.evidence = dossier["cuce"], dossier["title"], evidence
                row.is_synthetic, row.amount_attributed = False, None
            session.flush()
            exists = session.scalars(select(FireLink).where(
                FireLink.from_type == "fire_expenditure", FireLink.from_id == row.id,
                FireLink.to_type == "fire_season", FireLink.to_id == season.id)).first()
            if not exists:
                session.add(FireLink(from_type="fire_expenditure", from_id=row.id,
                                     to_type="fire_season", to_id=season.id,
                                     strength="FUERTEMENTE_VINCULADO",
                                     note="Proceso aeronave ↔ temporada VIDECI 2024",
                                     evidence={"ops_keys": ["operaciones", "litros_agua"]}))
        finish_fire_run(session, job, records_out=len(dossiers))
        session.commit()
        payload = {"status": "ok", "year": 2024, "dossiers": dossiers, "count": len(dossiers)}
        if write_artifact:
            write_json("f2_aeronaves_2024.json", payload)
        return payload
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()
