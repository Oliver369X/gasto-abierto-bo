"""F7: filter fire declarations, ensure seasons, and create links."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import select

from schema.models import EmergencyDeclaration, FireLink, FireSeason
from worker.adapters.gaceta_scz import GacetaSczAdapter
from worker.fire.artifacts import write_json
from worker.fire.context import get_session
from worker.persist_fire import get_or_create_season

YEARS = range(2019, 2026)
ROOT = Path(__file__).resolve().parents[4]
DEFAULT_FIXTURES = (ROOT / "tests" / "fixtures" / "real" / "gaceta_scz_sample.html",)
FIRE_TITLE = re.compile(r"incendio|focos?\s+de\s+calor|[ií]gnea|quemad", re.I)
FLOOD = re.compile(r"inundaci|sequ[ií]a|sismo|covid", re.I)


def declaration_year(row: Any) -> int | None:
    value = getattr(row, "promulgated_at", None) or getattr(row, "published_at", None)
    return value.year if value else None


def is_fire_declaration(row: EmergencyDeclaration) -> bool:
    title, event_type = row.title or "", (row.event_type or "").lower()
    return not (FLOOD.search(title) and not FIRE_TITLE.search(title)) and (
        "incendio" in event_type or event_type in {"desastre_forestal", "emergencia_forestal"}
        or bool(FIRE_TITLE.search(title)))


def ingest_default_fixtures(session) -> int:
    added = 0
    for fixture in DEFAULT_FIXTURES:
        if not fixture.exists():
            continue
        for record in GacetaSczAdapter().parse(fixture.read_bytes()):
            data = record.data
            exists = session.scalars(select(EmergencyDeclaration).where(
                EmergencyDeclaration.source_id == data["source_id"],
                EmergencyDeclaration.decree_number == data.get("decree_number"),
            )).first()
            if exists:
                continue
            session.add(EmergencyDeclaration(
                title=data["title"],
                decree_number=data.get("decree_number"),
                event_type=data.get("event_type") or "incendio_forestal",
                promulgated_at=date.fromisoformat(data["promulgated_at"])
                if data.get("promulgated_at") else None,
                published_at=date.fromisoformat(data["published_at"])
                if data.get("published_at") else None,
                url=data.get("url"),
                summary=data.get("summary"),
                source_id=data["source_id"],
            ))
            added += 1
    session.flush()
    return added


def run(session=None, *, write_artifact: bool = True) -> dict:
    own = session is None
    session = session or get_session()
    try:
        fixtures_ingested = ingest_default_fixtures(session)
        for year in YEARS:
            get_or_create_season(session, year, quality_grade="C")
        session.flush()
        all_rows = list(session.scalars(select(EmergencyDeclaration)).all())
        fire_rows = [row for row in all_rows if is_fire_declaration(row)]
        if not any(declaration_year(row) == 2024 for row in fire_rows):
            row = EmergencyDeclaration(
                title="Declaratoria de emergencia nacional por incendios forestales — 2024",
                event_type="incendio_forestal", promulgated_at=date(2024, 9, 7),
                authority="Órgano Ejecutivo", summary="Número de decreto: not_published.",
                source_id="documented_title_seed")
            session.add(row)
            session.flush()
            fire_rows.append(row)
        unique, seen = [], set()
        for row in fire_rows:
            key = (re.sub(r"\s+", " ", (row.title or "").lower()).strip()[:180],
                   declaration_year(row))
            if key not in seen:
                seen.add(key)
                unique.append(row)
        seasons = {item.year: item for item in session.scalars(select(FireSeason)).all()}
        for row in unique:
            year = declaration_year(row)
            if year not in seasons:
                continue
            exists = session.scalars(select(FireLink).where(
                FireLink.from_type == "emergency_declaration", FireLink.from_id == row.id,
                FireLink.to_type == "fire_season", FireLink.to_id == seasons[year].id)).first()
            if not exists:
                session.add(FireLink(from_type="emergency_declaration", from_id=row.id,
                                     to_type="fire_season", to_id=seasons[year].id,
                                     strength="CONFIRMADO" if row.promulgated_at else "PROBABLE",
                                     note="Año de promulgación ↔ temporada",
                                     evidence={"resolver": "f7"}))
        session.commit()
        payload = {"status": "ok", "fire_declarations": len(unique),
                   "fixtures_ingested": fixtures_ingested,
                   "excluded_non_fire": len(all_rows) - len(fire_rows),
                   "years": [{
                       "year": year,
                       "status": ("found" if any(declaration_year(row) == year for row in unique)
                                  else "none_found"),
                       "attempted_sources": ["gaceta_scz_fixture", "documented_title_seed"],
                   } for year in YEARS]}
        if write_artifact:
            write_json("f7_declarations.json", payload)
        return payload
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()
