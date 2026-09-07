"""F10: derive capability assets from confirmed expenditure titles."""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select

from common.fire.capability import classify_asset
from schema.models import FireCapabilityAsset, FireExpenditure
from worker.fire.artifacts import write_json
from worker.fire.context import get_session


def capability_from_title(title: str) -> tuple[str, str, str] | None:
    capability = classify_asset(title)
    if capability["asset_type"] == "other":
        return None
    ownership = {"purchased": "acquired"}.get(capability["ownership"], capability["ownership"])
    acquired_via = "alquiler_emergencia" if ownership == "rented" else "sicoes"
    asset_type = "guardian" if capability["asset_type"] == "sistema_aereo" and "guardian" in title.lower() else capability["asset_type"]
    return asset_type, ownership, acquired_via


def run(session=None, *, write_artifact: bool = True) -> dict:
    own = session is None
    session = session or get_session()
    try:
        assets = []
        rows = list(session.scalars(select(FireExpenditure).where(
            FireExpenditure.is_synthetic.is_(False))).all())
        for expenditure in rows:
            title = f"{expenditure.title} {expenditure.object_description or ''}"
            classified = classify_asset(title)
            if classified["asset_type"] == "other":
                continue
            existing = session.scalars(select(FireCapabilityAsset).where(
                FireCapabilityAsset.fire_expenditure_id == expenditure.id)).first()
            if existing:
                existing.year = expenditure.year
                existing.asset_type = classified["asset_type"]
                existing.name = expenditure.title
                existing.ownership = classified["ownership"]
                existing.entity_id = expenditure.paying_entity_id
                existing.territory_id = expenditure.beneficiary_territory_id
                existing.acquired_via = (
                    "alquiler_emergencia" if classified["ownership"] == "rented" else "sicoes"
                )
                existing.is_preventive = classified["is_preventive"]
                existing.source_id = expenditure.source_id
                assets.append(existing)
                continue
            asset = FireCapabilityAsset(
                year=expenditure.year, asset_type=classified["asset_type"],
                name=expenditure.title, ownership=classified["ownership"],
                entity_id=expenditure.paying_entity_id,
                territory_id=expenditure.beneficiary_territory_id,
                acquired_via="alquiler_emergencia" if classified["ownership"] == "rented" else "sicoes",
                fire_expenditure_id=expenditure.id,
                is_preventive=classified["is_preventive"],
                evidence={"fire_expenditure_code": expenditure.code,
                          "cuce": expenditure.cuce or "not_published",
                          "quantity_status": "not_published"},
                source_id=expenditure.source_id)
            session.add(asset)
            assets.append(asset)
        session.commit()
        series = defaultdict(lambda: {"preventive": 0, "reactive": 0})
        for asset in assets:
            series[asset.year]["preventive" if asset.is_preventive else "reactive"] += 1
        payload = {"status": "ok" if assets else "no_confirmed_titles_found",
                   "assets": [{"id": asset.id, "year": asset.year,
                               "asset_type": asset.asset_type, "name": asset.name,
                               "ownership": asset.ownership, "acquired_via": asset.acquired_via,
                               "is_preventive": asset.is_preventive}
                              for asset in assets],
                   "series": [{"year": year, **counts} for year, counts in sorted(series.items())]}
        if write_artifact:
            write_json("f10_capability.json", payload)
        return payload
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()
