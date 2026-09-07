"""SERNAP — áreas protegidas: presupuesto/rendiciones e incendios."""
from __future__ import annotations

import json
from pathlib import Path

from worker.adapters.base import Cursor, RawItem, StagingRecord


class SernapAdapter:
    source_id = "sernap"

    def discover(self, cursor: Cursor) -> list[RawItem]:
        if cursor.payload.get("fixture_path"):
            return [RawItem(uri=f"file://{cursor.payload['fixture_path']}", meta={})]
        return [
            RawItem(
                uri=cursor.payload.get(
                    "url", "https://www.sernap.gob.bo/index.php/datos/"
                ),
                meta={},
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
        rows = data if isinstance(data, list) else data.get("records") or []
        out: list[StagingRecord] = []
        for row in rows:
            rtype = row.get("record_type") or "fire_operational"
            payload = dict(row)
            payload.setdefault("entity_name", "SERNAP")
            payload.setdefault("level", "nacional")
            payload.setdefault("source_id", self.source_id)
            out.append(StagingRecord(record_type=rtype, data=payload))
        return out
