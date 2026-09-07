"""F8: ingest FIRMS detections and build deterministic grid clusters."""
from __future__ import annotations

import csv
import io
import os
import urllib.request
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from common.fire.geo_bbox import assign_department
from schema.models import ActiveFireDetection, FireCluster
from worker.fire.artifacts import write_json
from worker.fire.context import get_session

SOURCE = "VIIRS_SNPP_NRT"


def cluster_detections(detections: list[Any], grid_size: Decimal = Decimal("0.25")) -> list[list[Any]]:
    groups = defaultdict(list)
    for row in detections:
        if "sample" in (getattr(row, "source_id", "") or "").lower():
            continue
        if row.latitude is None or row.longitude is None:
            continue
        key = (int(getattr(row, "year", 0)), int(Decimal(str(row.latitude)) / grid_size),
               int(Decimal(str(row.longitude)) / grid_size))
        groups[key].append(row)
    return [sorted(group, key=lambda item: item.id) for group in groups.values()]


def _fetch(key: str) -> list[dict[str, str]]:
    url = f"https://firms.modaps.eosdis.nasa.gov/api/country/csv/{key}/{SOURCE}/BOL/2"
    with urllib.request.urlopen(url, timeout=30) as response:
        return list(csv.DictReader(io.StringIO(response.read().decode("utf-8"))))


def _insert(session, records: list[dict[str, str]]) -> int:
    inserted = 0
    for record in records:
        acquired, lat, lon = date.fromisoformat(record["acq_date"]), Decimal(record["latitude"]), Decimal(record["longitude"])
        exists = session.scalars(select(ActiveFireDetection).where(
            ActiveFireDetection.acq_date == acquired, ActiveFireDetection.latitude == lat,
            ActiveFireDetection.longitude == lon, ActiveFireDetection.source_id == "firms")).first()
        if exists:
            continue
        session.add(ActiveFireDetection(year=acquired.year, acq_date=acquired, latitude=lat,
                                        longitude=lon, brightness=Decimal(record["bright_ti4"]) if record.get("bright_ti4") else None,
                                        frp=Decimal(record["frp"]) if record.get("frp") else None,
                                        confidence=record.get("confidence"), satellite=record.get("satellite"),
                                        department=assign_department(lat, lon),
                                        source_id="firms"))
        inserted += 1
    session.flush()
    return inserted


def _create_clusters(session, detections) -> int:
    old = list(session.scalars(select(FireCluster).where(FireCluster.source_id == "firms_grid_f8")).all())
    old_ids = {row.id for row in old}
    if old_ids:
        for detection in session.scalars(select(ActiveFireDetection).where(
                ActiveFireDetection.cluster_id.in_(old_ids))).all():
            detection.cluster_id = None
        session.flush()
        for cluster in old:
            session.delete(cluster)
        session.flush()
    created = 0
    for group in cluster_detections(detections):
        pending = [row for row in group if row.cluster_id is None]
        if len(pending) < 2:
            continue
        cluster = FireCluster(year=pending[0].year,
                              start_date=min((r.acq_date for r in pending if r.acq_date), default=None),
                              end_date=max((r.acq_date for r in pending if r.acq_date), default=None),
                              centroid_lat=sum((r.latitude for r in pending), Decimal("0")) / len(pending),
                              centroid_lon=sum((r.longitude for r in pending), Decimal("0")) / len(pending),
                              detection_count=len(pending),
                              max_frp=max((r.frp for r in pending if r.frp is not None), default=None),
                              meta={"method": "decimal_grid", "grid_degrees": "0.25"},
                              source_id="firms_grid_f8")
        session.add(cluster)
        session.flush()
        for row in pending:
            row.cluster_id = cluster.id
        created += 1
    return created


def run(session=None, *, write_artifact: bool = True) -> dict:
    own = session is None
    session = session or get_session()
    try:
        samples = list(session.scalars(select(ActiveFireDetection).where(
            ActiveFireDetection.source_id.ilike("%sample%"))).all())
        for row in samples:
            session.delete(row)
        session.flush()
        key = os.getenv("MAP_KEY") or os.getenv("EARTHDATA_MAP_KEY")
        live_flag = os.getenv("FETCH_FIRMS_LIVE", "").strip() in {"1", "true", "TRUE", "yes"}
        inserted, live = 0, "blocked_missing_MAP_KEY"
        if not key:
            live = "blocked_missing_MAP_KEY"
        elif not live_flag:
            live = "key_present_fetch_disabled"
        else:
            inserted, live = _insert(session, _fetch(key)), "fetched"
        real = list(session.scalars(select(ActiveFireDetection).where(
            ~ActiveFireDetection.source_id.ilike("%sample%"))).all())
        assigned = 0
        for detection in real:
            if detection.department or detection.latitude is None or detection.longitude is None:
                continue
            detection.department = assign_department(detection.latitude, detection.longitude)
            assigned += bool(detection.department)
        clusters = _create_clusters(session, real)
        session.commit()
        payload = {"status": "ok", "live_fetch": live, "samples_purged": len(samples),
                   "detections_ingested": inserted, "real_detections": len(real),
                   "departments_assigned": assigned,
                   "clusters_created": clusters}
        if write_artifact:
            write_json("f8_firms_status.json", payload)
        return payload
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()
