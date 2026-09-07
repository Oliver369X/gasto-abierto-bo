"""F5: classify offline SICOES rows and upsert fire expenditures."""
from __future__ import annotations

import csv
import os
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import select

from common.fire.classify import classify_fire_text, is_fire_related
from schema.models import FireAttribution, FireCycle, FireExpenditure
from worker.fire.artifacts import write_json
from worker.fire.context import finish_fire_run, get_session, start_fire_run
from worker.fire.repository import get_exp_by_cuce
from worker.persist import get_or_create_entity, get_or_create_supplier
from worker.persist_fire import get_or_create_season, get_or_create_territory

ROOT = Path(__file__).resolve().parents[4]
CORPUS = ROOT / "tests" / "fixtures" / "real" / "corpus" / "by_year"
ENT_RE = re.compile(r"Ministerio De Defensa|VIDECI|ABT|Autoridad.*Bosques|SERNAP|Areas Protegidas|Medio Ambiente|Santa Cruz|Beni|Pando", re.I)
DEPARTMENTS = {"santa cruz": ("Santa Cruz", "santa-cruz"), "beni": ("Beni", "beni"), "pando": ("Pando", "pando")}


def run_enrich(session, *, write_artifact: bool = True, limit: int = 25) -> dict:
    """Enrich AERO and highest-value fire CUCEs; live access always requires PROXY_URL."""
    require_proxy = os.getenv("REQUIRE_PROXY_FOR_LIVE", "1").strip() not in {"0", "false", "FALSE"}
    if require_proxy and not os.getenv("PROXY_URL", "").strip():
        payload = {
            "status": "blocked_no_proxy",
            "enriched": 0,
            "note": "PROXY_URL required for live SICOES enrich (REQUIRE_PROXY_FOR_LIVE=1).",
        }
        if write_artifact:
            write_json("f05_enrich_cuce.json", payload)
        return payload
    from worker.enrich_sicoes import enrich_sicoes_cuce

    rows = list(session.scalars(select(FireExpenditure).where(
        FireExpenditure.cuce.is_not(None),
        FireExpenditure.is_synthetic.is_(False),
    )).all())
    rows.sort(key=lambda row: (
        0 if "AERO" in (row.code or "") else 1,
        -(row.amount_contract or Decimal("0")),
    ))
    results = []
    for row in rows[:limit]:
        try:
            results.append(enrich_sicoes_cuce(session, row.cuce))
        except Exception as exc:
            results.append({"ok": False, "cuce": row.cuce, "error": str(exc)})
    session.commit()
    payload = {
        "status": "ok",
        "attempted": len(results),
        "enriched": sum(bool(item.get("enriched") or item.get("ok")) for item in results),
        "results": results,
    }
    if write_artifact:
        write_json("f05_enrich_cuce.json", payload)
    return payload


def _amount(value) -> Decimal | None:
    try:
        return Decimal(str(value).replace(",", "").strip()) if value and str(value).strip() else None
    except (InvalidOperation, ValueError):
        return None


def _bucket(attribution: str, has_amount: bool) -> tuple[str, str, Decimal]:
    if attribution == "directo":
        return "probable", "keyword_share" if has_amount else "none", Decimal("0.750" if has_amount else "0.700")
    if attribution == "probable":
        return "probable", "keyword_share", Decimal("0.550")
    if attribution == "parcial":
        return "parcial", "pro_rata", Decimal("0.500")
    return "indirecto", "none", Decimal("0.400")


def upsert_row(session, *, year: int, row: dict, clf, run_id: int):
    cuce = (row.get("cuce") or "").strip()
    if not cuce:
        return None
    description = (row.get("description") or "").strip()
    entity_name = (row.get("entity") or "").strip() or "Entidad no publicada"
    amount = _amount(row.get("amount"))
    bucket, allocation, confidence = _bucket(clf.attribution, amount is not None)
    season = get_or_create_season(session, year, quality_grade="C")
    entity = get_or_create_entity(session, entity_name, level="nacional",
                                  source_id="sicoes_offline", run_id=run_id)
    supplier = None
    if (row.get("supplier") or "").strip():
        supplier = get_or_create_supplier(session, row["supplier"].strip(),
                                          source_id="sicoes_offline", run_id=run_id)
    territory = None
    blob = f"{row.get('department', '')} {description} {entity_name}".lower()
    for key, (name, slug) in DEPARTMENTS.items():
        if key in blob:
            territory = get_or_create_territory(session, name, level="departamento", slug=slug)
            break
    evidence = {"corpus_year_file": f"sicoes_{year}.csv", "matched_terms": clf.matched_terms,
                "rules_fired": list(clf.rules_fired), "evidence_span": clf.evidence_span,
                "recovery_status": "amount_not_published" if amount is None else "amount_from_offline_mirror",
                "f5_persisted": True}
    expenditure = get_exp_by_cuce(session, cuce)
    values = dict(year=year, season_id=season.id, title=description[:1024] or f"Proceso SICOES {cuce}",
                  object_description=description or None, attribution=FireAttribution(clf.attribution),
                  confidence_score=clf.confidence_score, classification_method=clf.classification_method,
                  cycle=FireCycle(clf.cycle), paying_entity_id=entity.id,
                  supplier_id=supplier.id if supplier else None,
                  beneficiary_territory_id=territory.id if territory else None,
                  amount_contract=amount, amount_attributed=amount if clf.attribution in {"directo", "probable", "parcial"} else None,
                  amount_attributed_base=amount if clf.attribution in {"directo", "probable", "parcial"} else None,
                  amount_total=amount, allocation_method=allocation, allocation_confidence=confidence,
                  ledger_bucket=bucket, is_synthetic=False, quality_grade="B" if amount else "C",
                  recovery_status=evidence["recovery_status"], evidence=evidence, source_id="sicoes_offline")
    if expenditure is None:
        safe = re.sub(r"[^A-Za-z0-9]+", "", cuce)[-12:] or "NOCUCE"
        expenditure = FireExpenditure(code=f"FIRE-BO-{year}-S{safe}", cuce=cuce, **values)
        session.add(expenditure)
    else:
        for name, value in values.items():
            if value is not None or name not in {"supplier_id", "beneficiary_territory_id"}:
                setattr(expenditure, name, value)
        expenditure.evidence = {**(expenditure.evidence or {}), **evidence}
    session.flush()
    return expenditure


def run(session=None, *, write_artifact: bool = True) -> dict:
    own = session is None
    session = session or get_session()
    persisted, by_year = [], {}
    try:
        job = start_fire_run(session, "f5_sicoes_fire", {"corpus": str(CORPUS)})
        for csv_path in sorted(CORPUS.glob("sicoes_*.csv")):
            year = int(csv_path.stem.removeprefix("sicoes_"))
            stats = {"candidates": 0, "persisted_directo": 0, "persisted_probable": 0,
                     "discarded": 0, "skipped_no_cuce": 0}
            with csv_path.open(encoding="utf-8", errors="replace", newline="") as stream:
                for row in csv.DictReader(stream):
                    entity, description = row.get("entity") or "", row.get("description") or ""
                    if not ENT_RE.search(f"{entity} {description}"):
                        continue
                    clf = classify_fire_text(object_description=description,
                                             modality=row.get("modality"), title=entity)
                    if not is_fire_related(clf):
                        stats["discarded"] += 1
                        continue
                    stats["candidates"] += 1
                    if clf.attribution == "probable" and not re.search(
                            r"Ministerio De Defensa|VIDECI|ABT|SERNAP", entity, re.I):
                        continue
                    expenditure = upsert_row(session, year=year, row=row, clf=clf, run_id=job.id)
                    if expenditure is None:
                        stats["skipped_no_cuce"] += 1
                        continue
                    stats["persisted_directo" if clf.attribution == "directo" else "persisted_probable"] += 1
                    persisted.append({"id": expenditure.id, "code": expenditure.code,
                                      "year": year, "cuce": expenditure.cuce,
                                      "attribution": clf.attribution,
                                      "ledger_bucket": expenditure.ledger_bucket})
            by_year[str(year)] = stats
            session.commit()
        finish_fire_run(session, job, records_out=len(persisted))
        session.commit()
        payload = {"status": "ok", "by_year": by_year, "persisted_total": len(persisted),
                   "persisted": persisted, "note": "Offline mirror rows remain probable until documentary quality A.",
                   "enrich": run_enrich(session, write_artifact=write_artifact)}
        if write_artifact:
            write_json("f5_sicoes_fire_backfill.json", payload)
        return payload
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()
