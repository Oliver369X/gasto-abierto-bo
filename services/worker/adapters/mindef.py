"""Ministerio de Defensa — Rendición Pública de Cuentas (incendios / VIDECI)."""
from __future__ import annotations

import json
from pathlib import Path

from worker.adapters.base import Cursor, RawItem, StagingRecord

RPC_2024_URL = (
    "https://www.mindef.gob.bo/wp-content/uploads/2026/01/"
    "12032025_INFORME_RPCFinal_2024_V15.pdf"
)


class MindefAdapter:
    """Parse MINDEF RPC JSON fixtures (PDF text extraction offline)."""

    source_id = "mindef"

    def discover(self, cursor: Cursor) -> list[RawItem]:
        if cursor.payload.get("fixture_path"):
            return [RawItem(uri=f"file://{cursor.payload['fixture_path']}", meta={})]
        # Default offline fixture relative to repo tests/
        return [
            RawItem(
                uri=cursor.payload.get("url", RPC_2024_URL),
                meta={"kind": "rpc_pdf"},
            )
        ]

    def fetch(self, item: RawItem) -> bytes:
        if item.uri.startswith("file://"):
            path = item.uri[7:]
            return Path(path).read_bytes()
        from common.http_client import assert_live_proxy_ok, request_with_retry

        assert_live_proxy_ok()
        return request_with_retry("GET", item.uri).content

    def parse(self, raw: bytes) -> list[StagingRecord]:
        # Prefer structured JSON fixtures; fall back to pdfplumber text scan.
        text_try = raw.decode("utf-8", errors="ignore").lstrip()
        if text_try.startswith("{") or text_try.startswith("["):
            return self._parse_json(text_try)
        return self._parse_pdf_bytes(raw)

    def _parse_json(self, text: str) -> list[StagingRecord]:
        data = json.loads(text)
        if isinstance(data, list):
            items = data
        else:
            items = data.get("records") or data.get("operational_outputs") or [data]
        out: list[StagingRecord] = []
        for item in items:
            rtype = item.get("record_type") or "fire_operational"
            out.append(StagingRecord(record_type=rtype, data=dict(item)))
        # Always attach source document metadata if present at root
        if isinstance(data, dict) and data.get("document"):
            doc = data["document"]
            out.append(
                StagingRecord(
                    record_type="document",
                    data={
                        "url": doc.get("url") or RPC_2024_URL,
                        "mime": doc.get("mime") or "application/pdf",
                        "sha256": doc.get("sha256"),
                        "source_id": self.source_id,
                    },
                )
            )
        return out

    def _parse_pdf_bytes(self, raw: bytes) -> list[StagingRecord]:
        try:
            import pdfplumber
        except ImportError:
            return []
        out: list[StagingRecord] = []
        with pdfplumber.open(__import__("io").BytesIO(raw)) as pdf:
            full = "\n".join((p.extract_text() or "") for p in pdf.pages)
        # Heuristic extraction of known 2024 VIDECI fire metrics
        patterns = [
            ("bomberos_forestales", r"([\d\.]+)\s*bomberos\s+forestales", "personas"),
            ("incendios_mitigados", r"([\d\.]+)\s*incendios\s+forestales\s+mitigados", "incendios"),
            ("operaciones", r"([\d\.]+)\s*operaciones", "operaciones"),
            ("litros_agua", r"([\d\.]+)\s*litros", "litros"),
        ]
        import re

        for key, pat, unit in patterns:
            m = re.search(pat, full, re.I)
            if m:
                raw_n = m.group(1).replace(".", "").replace(",", "")
                try:
                    val = float(raw_n)
                except ValueError:
                    continue
                out.append(
                    StagingRecord(
                        record_type="fire_operational",
                        data={
                            "year": 2024,
                            "metric_key": key,
                            "metric_label": key.replace("_", " ").title(),
                            "value_numeric": val,
                            "unit": unit,
                            "entity_name": "Ministerio de Defensa",
                            "source_id": self.source_id,
                            "evidence_quote": m.group(0)[:500],
                        },
                    )
                )
        out.append(
            StagingRecord(
                record_type="document",
                data={
                    "url": RPC_2024_URL,
                    "mime": "application/pdf",
                    "source_id": self.source_id,
                },
            )
        )
        return out
