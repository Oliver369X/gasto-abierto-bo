from __future__ import annotations

import io
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from common.money import parse_money
from worker.adapters.base import Cursor, RawItem, StagingRecord


class GadSczAdapter:
    source_id = "gad_scz"
    base = "https://santacruz.gob.bo"

    def discover(self, cursor: Cursor) -> list[RawItem]:
        if cursor.payload.get("fixture_path"):
            return [RawItem(uri=f"file://{cursor.payload['fixture_path']}", meta={})]
        return [RawItem(uri=self.base, meta={})]

    def fetch(self, item: RawItem) -> bytes:
        if item.uri.startswith("file://"):
            with open(item.uri[7:], "rb") as f:
                return f.read()
        from common.http_client import assert_live_proxy_ok, request_with_retry

        assert_live_proxy_ok()
        return request_with_retry("GET", item.uri).content

    def parse(self, raw: bytes) -> list[StagingRecord]:
        # PDF bytes?
        if raw[:4] == b"%PDF":
            return GamSczAdapter()._parse_pdf_bytes(raw, entity="GAD Santa Cruz", level="departamental")

        soup = BeautifulSoup(raw, "lxml")
        out: list[StagingRecord] = []
        for a in soup.select("a[href$='.pdf']"):
            href = urljoin(self.base, a.get("href") or "")
            text = a.get_text(" ", strip=True) or href
            out.append(
                StagingRecord(
                    record_type="document",
                    data={
                        "url": href,
                        "title": text,
                        "entity_name": "GAD Santa Cruz",
                        "source_id": self.source_id,
                        "mime": "application/pdf",
                    },
                )
            )
        for script in soup.select("script[type='application/json']"):
            import json

            try:
                data = json.loads(script.string or "{}")
            except json.JSONDecodeError:
                continue
            if "presupuesto_inicial" in data:
                out.append(
                    StagingRecord(
                        record_type="budget",
                        data={
                            "entity_name": "GAD Santa Cruz",
                            "level": "departamental",
                            "department": "Santa Cruz",
                            "year": int(data.get("gestion", 2025)),
                            "initial_amount": str(parse_money(data.get("presupuesto_inicial")) or ""),
                            "current_amount": str(parse_money(data.get("presupuesto_vigente")) or ""),
                            "executed_amount": str(parse_money(data.get("ejecucion")) or ""),
                            "source_id": self.source_id,
                        },
                    )
                )
        return out


class GamSczAdapter:
    source_id = "gam_scz"
    base = "https://www.gmsantacruz.gob.bo"

    def discover(self, cursor: Cursor) -> list[RawItem]:
        if cursor.payload.get("fixture_path"):
            return [RawItem(uri=f"file://{cursor.payload['fixture_path']}", meta={})]
        return [
            RawItem(
                uri=f"{self.base}/Publicaciones-Municipales/Rendiciones-Publicas/",
                meta={},
            )
        ]

    def fetch(self, item: RawItem) -> bytes:
        if item.uri.startswith("file://"):
            with open(item.uri[7:], "rb") as f:
                return f.read()
        from common.http_client import assert_live_proxy_ok, request_with_retry

        assert_live_proxy_ok()
        return request_with_retry("GET", item.uri).content

    def parse(self, raw: bytes) -> list[StagingRecord]:
        if raw[:4] == b"%PDF":
            return self._parse_pdf_bytes(
                raw, entity="GAM Santa Cruz de la Sierra", level="municipal"
            )
        text = raw.decode("utf-8", errors="replace")
        if "<html" in text.lower() or "<!doctype" in text.lower():
            soup = BeautifulSoup(raw, "lxml")
            out: list[StagingRecord] = []
            for a in soup.select("a[href$='.pdf']"):
                out.append(
                    StagingRecord(
                        record_type="document",
                        data={
                            "url": urljoin(self.base, a.get("href") or ""),
                            "title": a.get_text(" ", strip=True),
                            "entity_name": "GAM Santa Cruz de la Sierra",
                            "source_id": self.source_id,
                            "mime": "application/pdf",
                        },
                    )
                )
            return out
        return self._parse_pdf_text(
            text, entity="GAM Santa Cruz de la Sierra", level="municipal"
        )

    def _parse_pdf_bytes(self, raw: bytes, *, entity: str, level: str) -> list[StagingRecord]:
        try:
            import pdfplumber
        except ImportError:
            return []
        text_parts: list[str] = []
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for page in pdf.pages[:30]:
                text_parts.append(page.extract_text() or "")
        return self._parse_pdf_text("\n".join(text_parts), entity=entity, level=level)

    def _parse_pdf_text(self, text: str, *, entity: str, level: str) -> list[StagingRecord]:
        def grab(label: str):
            m = re.search(rf"{label}\s*[:\-]?\s*([\d\.,]+)", text, re.I)
            return m.group(1) if m else None

        initial = grab(r"PRESUPUESTO\s+INICIAL")
        vigente = grab(r"PRESUPUESTO\s+VIGENTE")
        ejec = grab(r"EJECUCI[OÓ]N(?:\s+FINANCIERA)?")
        year_m = re.search(r"GESTI[OÓ]N\s+(\d{4})", text, re.I)
        if not any([initial, vigente, ejec]):
            return [
                StagingRecord(
                    record_type="document",
                    data={
                        "url": "",
                        "title": f"PDF texto {entity}",
                        "entity_name": entity,
                        "source_id": self.source_id,
                        "ocr_status": "pending" if len(text.strip()) < 40 else "n/a",
                    },
                )
            ]
        return [
            StagingRecord(
                record_type="budget",
                data={
                    "entity_name": entity,
                    "level": level,
                    "department": "Santa Cruz",
                    "year": int(year_m.group(1)) if year_m else 2025,
                    "initial_amount": str(parse_money(initial) or ""),
                    "current_amount": str(parse_money(vigente) or ""),
                    "executed_amount": str(parse_money(ejec) or ""),
                    "source_id": self.source_id,
                },
            )
        ]
