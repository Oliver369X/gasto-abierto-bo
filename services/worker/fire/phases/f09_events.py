"""F9: resolve canonical events from independent evidence families."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select

from schema.models import (BurnedArea, EmergencyDeclaration, FireCluster, FireEvent,
                           FireExpenditure, FireLink, FireSeason, OperationalOutput, Territory)
from worker.fire.artifacts import write_json
from worker.fire.context import get_session
from worker.persist_fire import get_or_create_season, get_or_create_territory


def confidence_for_sources(count: int) -> tuple[str, Decimal]:
    return ("multi_source", Decimal("0.800")) if count >= 2 else ("single_source", Decimal("0.500"))


def run(session=None, *, write_artifact: bool = True) -> dict:
    own = session is None
    session = session or get_session()
    created = []
    try:
        scz = get_or_create_territory(session, "Santa Cruz", level="departamento", slug="santa-cruz")
        for year in range(2019, 2026):
            get_or_create_season(session, year, quality_grade="C")
        session.flush()
        seasons = {row.year: row for row in session.scalars(select(FireSeason)).all()}
        territories = {row.id: row for row in session.scalars(select(Territory)).all()}
        buckets = defaultdict(lambda: defaultdict(list))
        sources = [("ops", "operational_output", OperationalOutput, "territory_id"),
                   ("burned", "burned_area", BurnedArea, "territory_id"),
                   ("satellite", "fire_cluster", FireCluster, "territory_id")]
        for family, kind, model, territory_field in sources:
            for row in session.scalars(select(model)).all():
                buckets[(row.year, getattr(row, territory_field))][family].append((kind, row))
        for row in session.scalars(select(FireExpenditure)).all():
            if not row.is_synthetic:
                buckets[(row.year, row.beneficiary_territory_id)]["spend"].append(("fire_expenditure", row))
        for row in session.scalars(select(EmergencyDeclaration)).all():
            published = row.promulgated_at or row.published_at
            if published and "incendio" in f"{row.event_type} {row.title}".lower():
                buckets[(published.year, row.territory_id)]["declaration"].append(("emergency_declaration", row))
        for (year, territory_id), families in list(buckets.items()):
            if territory_id is None:
                for kind, row in families.get("ops", []):
                    blob = f"{row.metric_key} {row.metric_label} {row.evidence_quote or ''}".lower()
                    if "santa cruz" in blob or "scz" in blob:
                        buckets[(year, scz.id)]["ops"].append((kind, row))
        sequence = defaultdict(int)
        existing_codes = set(session.scalars(select(FireEvent.code)).all())
        for (year, territory_id), families in sorted(buckets.items(), key=lambda item: (item[0][0], item[0][1] or 0)):
            if year not in seasons or not families:
                continue
            names = sorted(families)
            if names == ["ops"] and not any("hect" in (row.metric_key or "").lower()
                                             for _, row in families["ops"]):
                continue
            sequence[year] += 1
            code = f"FIRE-EVENT-BO-{year}-{sequence[year]:03d}"
            while code in existing_codes:
                sequence[year] += 1
                code = f"FIRE-EVENT-BO-{year}-{sequence[year]:03d}"
            existing_codes.add(code)
            territory = territories.get(territory_id)
            event = session.scalars(select(FireEvent).where(
                FireEvent.season_id == seasons[year].id,
                FireEvent.territory_id == territory_id if territory_id is not None else FireEvent.territory_id.is_(None))).first()
            if event is None:
                event = FireEvent(code=code, season_id=seasons[year].id, territory_id=territory_id,
                                  name=f"Temporada incendios {territory.name if territory else 'Bolivia'} {year}")
                session.add(event)
                session.flush()
            label, confidence = confidence_for_sources(len(names))
            event.confidence = confidence
            event.sources = sorted({f"{family}:{getattr(row, 'source_id', kind)}"
                                    for family, rows in families.items() for kind, row in rows[:5]})
            event.meta = {**(event.meta or {}), "confidence_label": label,
                          "families": names, "resolver": "f9"}
            for family, rows in families.items():
                for kind, row in rows[:20]:
                    exists = session.scalars(select(FireLink).where(
                        FireLink.from_type == kind, FireLink.from_id == row.id,
                        FireLink.to_type == "fire_event", FireLink.to_id == event.id)).first()
                    if not exists:
                        session.add(FireLink(from_type=kind, from_id=row.id, to_type="fire_event",
                                             to_id=event.id,
                                             strength="FUERTEMENTE_VINCULADO" if len(names) >= 2 else "POSIBLE",
                                             note="Familia de evidencia independiente.",
                                             evidence={"resolver": "f9", "family": family}))
            created.append({"code": event.code, "year": year,
                            "territory": territory.name if territory else "Bolivia",
                            "families": names, "confidence_label": label,
                            "confidence": str(confidence), "sources": event.sources})
        session.commit()
        payload = {"status": "ok", "events": created, "count": len(created),
                   "scz_2024_multi_source": [row for row in created if row["year"] == 2024
                                             and row["territory"] == "Santa Cruz"
                                             and row["confidence_label"] == "multi_source"]}
        if write_artifact:
            write_json("f9_events.json", payload)
        return payload
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()
