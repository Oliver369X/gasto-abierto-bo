"""Gaceta Oficial Santa Cruz — declaratorias de emergencia (incendios)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from worker.adapters.base import Cursor, RawItem, StagingRecord


class GacetaSczAdapter:
    source_id = "gaceta_scz"
    base_url = "https://gacetaoficial.santacruz.gob.bo"
    default_entity = "Gobierno Autónomo Departamental de Santa Cruz"
    default_territory = "Santa Cruz"
    default_territory_level = "departamento"

    def discover(self, cursor: Cursor) -> list[RawItem]:
        if cursor.payload.get("fixture_path"):
            return [RawItem(uri=f"file://{cursor.payload['fixture_path']}", meta={})]
        return [
            RawItem(
                uri=cursor.payload.get(
                    "url",
                    "https://gacetaoficial.santacruz.gob.bo/decretosdepartamentales",
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
            return self._parse_html(text)
        data = json.loads(text)
        rows = data if isinstance(data, list) else data.get("records") or []
        out: list[StagingRecord] = []
        for row in rows:
            blob = f"{row.get('title', '')} {row.get('summary', '')} {row.get('event_type', '')}"
            if not re.search(r"incendio|forestal|[ií]gnea|focos?\s+de\s+calor", blob, re.I):
                continue
            out.append(
                StagingRecord(
                    record_type="emergency_declaration",
                    data={
                        "title": row.get("title"),
                        "decree_number": row.get("decree_number"),
                        "event_type": row.get("event_type") or "incendio_forestal",
                        "entity_name": row.get("entity_name")
                        or self.default_entity,
                        "territory_name": row.get("territory_name") or self.default_territory,
                        "territory_level": row.get("territory_level")
                        or self.default_territory_level,
                        "promulgated_at": row.get("promulgated_at"),
                        "published_at": row.get("published_at"),
                        "url": row.get("url"),
                        "summary": row.get("summary"),
                        "source_id": self.source_id,
                    },
                )
            )
        return out

    def _parse_html(self, text: str) -> list[StagingRecord]:
        soup = BeautifulSoup(text, "html.parser")
        nodes = soup.select("article, .decreto, .resultado, .item, li")
        out: list[StagingRecord] = []
        for node in nodes:
            title_node = node.select_one("h1, h2, h3, h4, .title, .titulo")
            title = title_node.get_text(" ", strip=True) if title_node else ""
            summary = node.get_text(" ", strip=True)
            if not re.search(r"incendio|forestal|[ií]gnea|focos?\s+de\s+calor", f"{title} {summary}", re.I):
                continue
            decree = re.search(r"(?:decreto(?:\s+departamental|\s+supremo)?\s*(?:n[°º.]?\s*)?)(\d+)", title, re.I)
            time = node.select_one("time")
            promulgated = time.get("datetime") if time else None
            link = node.select_one("a[href]")
            out.append(StagingRecord(
                record_type="emergency_declaration",
                data={
                    "title": title or summary[:300],
                    "decree_number": decree.group(1) if decree else None,
                    "event_type": "incendio_forestal",
                    "entity_name": self.default_entity,
                    "territory_name": self.default_territory,
                    "territory_level": self.default_territory_level,
                    "promulgated_at": promulgated,
                    "published_at": promulgated,
                    "url": urljoin(self.base_url, link["href"]) if link else None,
                    "summary": summary[:1000],
                    "source_id": self.source_id,
                },
            ))
        return out
