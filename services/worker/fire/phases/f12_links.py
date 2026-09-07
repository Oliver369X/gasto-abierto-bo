"""F12: link aircraft spending to operations/events without cartesian joins."""
from __future__ import annotations

from sqlalchemy import select

from common.fire.linking import infer_strength, is_aerial_ops_blob
from schema.models import FireEvent, FireLink, FireSeason, OperationalOutput
from worker.fire.artifacts import write_json
from worker.fire.context import get_session
from worker.fire.repository import list_aero, purge_links_by_resolver


def _ensure_link(session, *, from_id: int, to_type: str, to_id: int,
                 strength: str, basis: list[str], note: str) -> FireLink:
    link = session.scalars(select(FireLink).where(
        FireLink.from_type == "fire_expenditure", FireLink.from_id == from_id,
        FireLink.to_type == to_type, FireLink.to_id == to_id)).first()
    evidence = {"resolver": "f12", "basis": basis, "causal_amount": "not_determinable"}
    if link:
        link.strength, link.note, link.evidence = strength, note, evidence
    else:
        link = FireLink(from_type="fire_expenditure", from_id=from_id, to_type=to_type,
                        to_id=to_id, strength=strength, note=note, evidence=evidence)
        session.add(link)
    session.flush()
    return link


def run(session=None, *, write_artifact: bool = True) -> dict:
    own = session is None
    session = session or get_session()
    output = []
    try:
        purged = purge_links_by_resolver(session, "f12")
        aircraft, operations = list_aero(session), list(session.scalars(select(OperationalOutput)).all())
        events = list(session.scalars(select(FireEvent)).all())
        season_year = {row.id: row.year for row in session.scalars(select(FireSeason)).all()}
        for expenditure in aircraft:
            expenditure.link_strength = "NO_DETERMINABLE"
            matched = []
            for operation in (row for row in operations if row.year == expenditure.year):
                blob = f"{operation.metric_key} {operation.metric_label} {operation.evidence_quote or ''}"
                if not is_aerial_ops_blob(blob):
                    continue
                explicit = bool((expenditure.cuce and expenditure.cuce.lower() in blob.lower())
                                or expenditure.code.lower() in blob.lower())
                strength = "CONFIRMADO" if explicit else "FUERTEMENTE_VINCULADO"
                basis = ["explicit_reference"] if explicit else ["same_year", "aerial_ops_vocab"]
                link = _ensure_link(session, from_id=expenditure.id, to_type="operational_output",
                                    to_id=operation.id, strength=strength, basis=basis,
                                    note="Misma temporada + vocabulario aéreo/ops; sin reparto causal.")
                matched.append(operation)
                output.append({"id": link.id, "from_code": expenditure.code,
                               "to_type": "operational_output", "to_id": operation.id,
                               "strength": strength, "basis": basis})
            for event in (row for row in events if season_year.get(row.season_id) == expenditure.year):
                same_territory = bool(expenditure.beneficiary_territory_id and event.territory_id
                                      and expenditure.beneficiary_territory_id == event.territory_id)
                explicit = expenditure.fire_event_id == event.id
                if not (explicit or ((same_territory or event.territory_id is None) and matched)):
                    continue
                strength = infer_strength(same_year=True, event_linked=same_territory,
                                          explicit_reference=explicit)
                basis = ["fire_event_id"] if explicit else ["same_year", "aerial_ops"] + (
                    ["territory"] if same_territory else ["national_event"])
                link = _ensure_link(session, from_id=expenditure.id, to_type="fire_event",
                                    to_id=event.id, strength=strength, basis=basis,
                                    note="Vínculo temporada/territorio; sin causalidad de hectáreas.")
                output.append({"id": link.id, "from_code": expenditure.code,
                               "to_type": "fire_event", "to_id": event.id,
                               "strength": strength, "basis": basis})
            if matched:
                expenditure.link_strength = "FUERTEMENTE_VINCULADO"
        session.commit()
        payload = {"status": "ok", "purged_previous_f12": purged, "links": output,
                   "count": len(output), "disclaimer": "Sin producto cartesiano ni montos causales inventados."}
        if write_artifact:
            write_json("f12_links.json", payload)
        return payload
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()
