"""ABT — ejecución presupuestaria / adquisiciones relacionadas con bosques."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from worker.adapters.base import Cursor, RawItem, StagingRecord


class AbtAdapter:
    """Parse ABT budget execution fixtures (CSV/JSON)."""

    source_id = "abt"

    def discover(self, cursor: Cursor) -> list[RawItem]:
        if cursor.payload.get("fixture_path"):
            return [RawItem(uri=f"file://{cursor.payload['fixture_path']}", meta={})]
        return [
            RawItem(
                uri=cursor.payload.get(
                    "url",
                    "https://www.abt.gob.bo/index.php/institucion/plan-estrategico/"
                    "programado-ejecutado-y-resultados",
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
        if text.startswith("{") or text.startswith("["):
            return self._parse_json(text)
        if "," in text[:200] or ";" in text[:200]:
            return self._parse_csv(text)
        return []

    def _parse_json(self, text: str) -> list[StagingRecord]:
        data = json.loads(text)
        rows = data if isinstance(data, list) else data.get("records") or data.get("budgets") or []
        out: list[StagingRecord] = []
        for row in rows:
            rtype = row.get("record_type") or "budget"
            payload = dict(row)
            payload.setdefault("entity_name", "Autoridad de Fiscalización y Control Social de Bosques y Tierra")
            payload.setdefault("level", "nacional")
            payload.setdefault("source_id", self.source_id)
            out.append(StagingRecord(record_type=rtype, data=payload))
        return out

    def _parse_csv(self, text: str) -> list[StagingRecord]:
        dialect = csv.Sniffer().sniff(text[:1024], delimiters=",;")
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        out: list[StagingRecord] = []
        for row in reader:
            out.append(
                StagingRecord(
                    record_type="budget",
                    data={
                        "entity_name": row.get("entity_name")
                        or "Autoridad de Fiscalización y Control Social de Bosques y Tierra",
                        "level": "nacional",
                        "year": int(row.get("year") or row.get("gestion") or 2024),
                        "program_project": row.get("program_project") or row.get("descripcion"),
                        "budget_item": row.get("budget_item") or row.get("partida"),
                        "initial_amount": row.get("initial_amount") or row.get("presupuesto_inicial"),
                        "modified_amount": row.get("modified_amount") or row.get("modificaciones"),
                        "current_amount": row.get("current_amount") or row.get("presupuesto_vigente"),
                        "executed_amount": row.get("executed_amount") or row.get("ejecutado"),
                        "source_id": self.source_id,
                    },
                )
            )
        return out
