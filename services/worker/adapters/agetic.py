from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from typing import Any

import httpx

from common.cuce import normalize_cuce
from common.http_client import assert_live_proxy_ok, get_http_client, request_with_retry
from worker.adapters.base import Cursor, RawItem, StagingRecord

# Known / high-value contracting packages on datos.gob.bo (expandable via env).
DEFAULT_PACKAGE_IDS = [
    "contrataciones-agetic-2019-estandar-ocp",
]


class AgeticAdapter:
    """CKAN client for datos.gob.bo — multi-package discover for deep history."""

    source_id = "agetic"
    base_url = "https://datos.gob.bo"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or get_http_client()

    def _package_ids(self, cursor: Cursor) -> list[str]:
        if cursor.payload.get("package_id"):
            return [str(cursor.payload["package_id"])]
        env = os.getenv("AGETIC_PACKAGE_IDS", "").strip()
        if env:
            return [p.strip() for p in env.split(",") if p.strip()]
        # Live deep mode: also package_search for contracting-related datasets
        if cursor.payload.get("live") or os.getenv("LIVE_SCRAPE") == "1":
            found = self._search_packages(
                os.getenv("AGETIC_SEARCH_Q", "contratacion OR ocds OR sicoes")
            )
            return list(dict.fromkeys(DEFAULT_PACKAGE_IDS + found))
        return list(DEFAULT_PACKAGE_IDS)

    def _search_packages(self, query: str, *, rows: int | None = None) -> list[str]:
        rows = rows or int(os.getenv("AGETIC_SEARCH_ROWS", "25"))
        url = f"{self.base_url}/api/3/action/package_search"
        try:
            resp = request_with_retry(
                "GET",
                url,
                client=self.client,
                params={"q": query, "rows": rows},
            )
            results = resp.json().get("result", {}).get("results", []) or []
            return [r["name"] for r in results if r.get("name")]
        except Exception:  # noqa: BLE001 — soft-fail, keep defaults
            return []

    def discover(self, cursor: Cursor) -> list[RawItem]:
        if cursor.payload.get("fixture_path"):
            from pathlib import Path

            path = Path(cursor.payload["fixture_path"])
            if path.is_dir():
                files = sorted(
                    {
                        *path.glob("*.csv"),
                        *path.glob("*.json"),
                        *path.glob("**/*.csv"),
                        *path.glob("**/*.json"),
                    }
                )
                return [
                    RawItem(
                        uri=f"file://{p}",
                        meta={"package_id": "fixture", "format": p.suffix.lstrip(".")},
                    )
                    for p in files
                ]
            return [
                RawItem(
                    uri=f"file://{path}",
                    meta={"package_id": "fixture", "format": "fixture"},
                )
            ]

        assert_live_proxy_ok()
        max_resources = int(
            cursor.payload.get("max_resources")
            or os.getenv("AGETIC_MAX_RESOURCES", "50")
        )
        items: list[RawItem] = []
        for package_id in self._package_ids(cursor):
            url = f"{self.base_url}/api/3/action/package_show"
            try:
                resp = request_with_retry(
                    "GET", url, client=self.client, params={"id": package_id}
                )
                data = resp.json()
            except Exception:  # noqa: BLE001
                continue
            resources = data.get("result", {}).get("resources", []) or []
            for r in resources:
                if len(items) >= max_resources:
                    return items
                rurl = r.get("url")
                if not rurl:
                    continue
                fmt = (r.get("format") or "").lower()
                if fmt and fmt not in (
                    "csv",
                    "json",
                    "xlsx",
                    "xls",
                    "text/csv",
                    "application/json",
                    "",
                ):
                    # still allow unknown — many CKAN entries leave format blank
                    if fmt not in ("html", "pdf", "zip"):
                        pass
                    elif fmt in ("html", "pdf"):
                        continue
                items.append(
                    RawItem(
                        uri=rurl,
                        meta={
                            "package_id": package_id,
                            "resource_id": r.get("id"),
                            "format": fmt,
                            "name": r.get("name"),
                        },
                    )
                )
        return items

    def fetch(self, item: RawItem) -> bytes:
        if item.uri.startswith("file://"):
            path = item.uri[7:]
            with open(path, "rb") as f:
                return f.read()
        assert_live_proxy_ok()
        resp = request_with_retry("GET", item.uri, client=self.client)
        return resp.content

    def parse(self, raw: bytes) -> list[StagingRecord]:
        text = raw.decode("utf-8-sig", errors="replace")
        if text.lstrip().startswith("{") or text.lstrip().startswith("["):
            return self._parse_json(text)
        return self._parse_csv(text)

    def _parse_csv(self, text: str) -> list[StagingRecord]:
        reader = csv.DictReader(io.StringIO(text))
        out: list[StagingRecord] = []
        for row in reader:
            out.append(
                StagingRecord(
                    record_type="contract",
                    data={
                        "cuce": normalize_cuce(
                            row.get("cuce") or row.get("ocid") or row.get("id")
                        ),
                        "entity_name": row.get("entity")
                        or row.get("buyer")
                        or row.get("entidad")
                        or "Entidad desconocida",
                        "supplier_name": row.get("supplier")
                        or row.get("proveedor")
                        or row.get("awardee"),
                        "object_description": row.get("description")
                        or row.get("objeto")
                        or row.get("title"),
                        "amount": row.get("amount") or row.get("monto") or row.get("value"),
                        "modality": row.get("modality") or row.get("modalidad"),
                        "contract_date": row.get("date")
                        or row.get("fecha")
                        or row.get("awardDate"),
                        "status": row.get("status") or row.get("estado"),
                        "department": row.get("department") or row.get("departamento"),
                        "source_id": self.source_id,
                    },
                )
            )
        return out

    def _parse_json(self, text: str) -> list[StagingRecord]:
        data: Any = json.loads(text)
        rows = data if isinstance(data, list) else data.get("data") or data.get("releases") or [data]
        out: list[StagingRecord] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            buyer = row.get("buyer") or {}
            if isinstance(buyer, dict):
                entity_name = buyer.get("name") or "Entidad desconocida"
            else:
                entity_name = str(buyer)
            awards = row.get("awards") or [{}]
            award = awards[0] if awards else {}
            suppliers = award.get("suppliers") or [{}]
            supplier = suppliers[0] if suppliers else {}
            value = award.get("value") or row.get("value") or {}
            amount = value.get("amount") if isinstance(value, dict) else value
            out.append(
                StagingRecord(
                    record_type="contract",
                    data={
                        "cuce": normalize_cuce(row.get("ocid") or row.get("id")),
                        "entity_name": entity_name,
                        "supplier_name": supplier.get("name")
                        if isinstance(supplier, dict)
                        else None,
                        "object_description": row.get("tender", {}).get("title")
                        if isinstance(row.get("tender"), dict)
                        else row.get("title"),
                        "amount": amount,
                        "modality": (row.get("tender") or {}).get("procurementMethod")
                        if isinstance(row.get("tender"), dict)
                        else None,
                        "contract_date": award.get("date") or row.get("date"),
                        "status": award.get("status") or row.get("tag"),
                        "source_id": self.source_id,
                    },
                )
            )
        return out

    @staticmethod
    def content_hash(raw: bytes) -> str:
        return hashlib.sha256(raw).hexdigest()
