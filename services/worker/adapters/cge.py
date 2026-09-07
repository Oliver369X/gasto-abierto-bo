from __future__ import annotations

import os
import re
from pathlib import Path

from bs4 import BeautifulSoup

from worker.adapters.base import Cursor, RawItem, StagingRecord


class CgeAdapter:
    """Parse public CGE audit listing HTML (no DJBR).

    Live discover covers several public listing URLs (not only homepage).
    Offline: file or directory of HTML fixtures.
    """

    source_id = "cge"
    default_urls = (
        "https://www.contraloria.gob.bo/",
        "https://www.contraloria.gob.bo/portal/",
    )

    def discover(self, cursor: Cursor) -> list[RawItem]:
        fixture = cursor.payload.get("fixture_path")
        if fixture:
            path = Path(fixture)
            if path.is_dir():
                files = sorted({*path.glob("*.html"), *path.glob("**/*.html")})
                return [RawItem(uri=f"file://{p}", meta={}) for p in files]
            return [RawItem(uri=f"file://{path}", meta={})]

        env_urls = os.getenv("CGE_LIST_URLS", "").strip()
        if env_urls:
            urls = [u.strip() for u in env_urls.split(",") if u.strip()]
        else:
            urls = list(self.default_urls)
            # Optional year sweep for known path patterns
            years = os.getenv("CGE_YEARS", "2019,2020,2021,2022,2023,2024,2025")
            for y in years.split(","):
                y = y.strip()
                if y.isdigit():
                    urls.append(
                        f"https://www.contraloria.gob.bo/?s=informe+{y}"
                    )
        return [RawItem(uri=u, meta={}) for u in urls]

    def fetch(self, item: RawItem) -> bytes:
        if item.uri.startswith("file://"):
            with open(item.uri[7:], "rb") as f:
                return f.read()
        from common.http_client import assert_live_proxy_ok, request_with_retry

        assert_live_proxy_ok()
        return request_with_retry("GET", item.uri).content

    def parse(self, raw: bytes) -> list[StagingRecord]:
        soup = BeautifulSoup(raw, "lxml")
        out: list[StagingRecord] = []
        seen: set[str] = set()
        for a in soup.select("a[href]"):
            href = a.get("href") or ""
            text = a.get_text(" ", strip=True)
            if not text:
                continue
            lower = (href + " " + text).lower()
            if not (
                "audit" in lower
                or "informe" in lower
                or "dictamen" in lower
                or href.endswith(".pdf")
            ):
                continue
            key = href or text
            if key in seen:
                continue
            seen.add(key)
            year = None
            m = re.search(r"(20\d{2})", text + " " + href)
            if m:
                year = int(m.group(1))
            out.append(
                StagingRecord(
                    record_type="audit",
                    data={
                        "title": text[:1024],
                        "url": href,
                        "year": year,
                        "entity_name": None,
                        "findings_summary": None,
                        "source_id": self.source_id,
                    },
                )
            )
        return out
