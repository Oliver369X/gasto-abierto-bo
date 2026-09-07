"""NASA FIRMS — focos de calor (resultados espaciales, no gasto)."""
from __future__ import annotations

import json
from pathlib import Path

from worker.adapters.base import Cursor, RawItem, StagingRecord


class FirmsAdapter:
    source_id = "firms"

    def discover(self, cursor: Cursor) -> list[RawItem]:
        if cursor.payload.get("fixture_path"):
            return [RawItem(uri=f"file://{cursor.payload['fixture_path']}", meta={})]
        # Live would use FIRMS API with MAP_KEY — not inventing endpoints.
        return [
            RawItem(
                uri=cursor.payload.get(
                    "url", "https://firms.modaps.eosdis.nasa.gov/"
                ),
                meta={"note": "use fixture or MAP_KEY API in live mode"},
            )
        ]

    def fetch(self, item: RawItem) -> bytes:
        if item.uri.startswith("file://"):
            return Path(item.uri[7:]).read_bytes()
        from common.http_client import assert_live_proxy_ok, request_with_retry

        assert_live_proxy_ok()
        return request_with_retry("GET", item.uri).content

    def parse(self, raw: bytes) -> list[StagingRecord]:
        text = raw.decode("utf-8", errors="ignore").lstrip()
        if not (text.startswith("{") or text.startswith("[")):
            return []
        data = json.loads(text)
        rows = data if isinstance(data, list) else data.get("detections") or data.get("records") or []
        out: list[StagingRecord] = []
        for row in rows:
            out.append(
                StagingRecord(
                    record_type="active_fire_detection",
                    data={
                        "year": row.get("year") or (str(row.get("acq_date") or "")[:4] or 2024),
                        "acq_date": row.get("acq_date") or row.get("date"),
                        "latitude": row.get("latitude") or row.get("lat"),
                        "longitude": row.get("longitude") or row.get("lon"),
                        "brightness": row.get("brightness"),
                        "frp": row.get("frp"),
                        "confidence": row.get("confidence"),
                        "satellite": row.get("satellite") or row.get("instrument") or "VIIRS",
                        "department": row.get("department"),
                        "municipality": row.get("municipality"),
                        "source_id": self.source_id,
                    },
                )
            )
        # Aggregate daily counts as operational outputs for the ledger UI
        by_year_dept: dict[tuple, int] = {}
        for row in rows:
            y = int(row.get("year") or (str(row.get("acq_date") or "2024")[:4]))
            dept = row.get("department") or "Bolivia"
            by_year_dept[(y, dept)] = by_year_dept.get((y, dept), 0) + 1
        for (y, dept), n in by_year_dept.items():
            out.append(
                StagingRecord(
                    record_type="fire_operational",
                    data={
                        "year": y,
                        "metric_key": f"firms_hotspots_{dept.lower().replace(' ', '_')}",
                        "metric_label": f"Focos FIRMS detectados — {dept}",
                        "value_numeric": n,
                        "unit": "focos",
                        "entity_name": "NASA FIRMS",
                        "territory_name": dept if dept != "Bolivia" else None,
                        "territory_level": "departamento" if dept != "Bolivia" else "pais",
                        "evidence_quote": "Foco de calor ≠ hectárea quemada. Dato satelital de fuego activo.",
                        "source_id": self.source_id,
                    },
                )
            )
        return out
