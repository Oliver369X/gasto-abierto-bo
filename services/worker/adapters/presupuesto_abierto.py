from __future__ import annotations

import json
import os
from pathlib import Path

from common.money import parse_money
from common.presupuesto_csv import parse_file_bytes
from worker.adapters.base import Cursor, RawItem, StagingRecord

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIRS = (
    ROOT / "tests" / "fixtures" / "real" / "presupuesto_abierto",
    ROOT / "tests" / "fixtures" / "presupuesto_abierto",
)


class PresupuestoAbiertoAdapter:
    """Parse Presupuesto Abierto exports: JSON fixtures, official CSV/Parquet.

    Offline: file or directory under tests/fixtures/presupuesto_abierto/ or
    tests/fixtures/real/presupuesto_abierto/ (CSV from `gasto fetch-presupuesto`).

    Live: comma-separated direct download URLs in PRESUPUESTO_ABIERTO_DOWNLOAD_URLS
    (copy from https://abierto.economiayfinanzas.gob.bo/descargas).
    """

    source_id = "presupuesto_abierto"
    DATA_EXTENSIONS = (".json", ".csv", ".parquet")

    def discover(self, cursor: Cursor) -> list[RawItem]:
        fixture = cursor.payload.get("fixture_path")
        if fixture:
            path = Path(fixture)
            if path.is_dir():
                files = sorted(
                    p
                    for ext in self.DATA_EXTENSIONS
                    for p in {*path.glob(f"*{ext}"), *path.glob(f"**/*{ext}")}
                )
                return [RawItem(uri=f"file://{p}", meta={"kind": "fixture"}) for p in files]
            return [RawItem(uri=f"file://{path}", meta={})]

        env_urls = os.getenv("PRESUPUESTO_ABIERTO_DOWNLOAD_URLS", "").strip()
        if env_urls:
            return [
                RawItem(uri=u.strip(), meta={"note": "official_download"})
                for u in env_urls.split(",")
                if u.strip()
            ]

        legacy = os.getenv("PRESUPUESTO_ABIERTO_URLS", "").strip()
        if legacy:
            return [
                RawItem(uri=u.strip(), meta={"note": "legacy_url"})
                for u in legacy.split(",")
                if u.strip()
            ]

        if cursor.payload.get("live"):
            from common.fetch_presupuesto_abierto import list_download_urls

            urls = list_download_urls(discover=True)
            if urls:
                return [
                    RawItem(uri=u, meta={"note": "discovered_download"})
                    for u in urls
                ]

        return self._fixture_items()

    def _fixture_items(self) -> list[RawItem]:
        items: list[RawItem] = []
        for directory in FIXTURE_DIRS:
            if not directory.is_dir():
                continue
            files = sorted(
                p
                for ext in self.DATA_EXTENSIONS
                for p in {*directory.glob(f"*{ext}"), *directory.glob(f"**/*{ext}")}
            )
            for path in files:
                items.append(RawItem(uri=f"file://{path}", meta={"kind": "fixture_fallback"}))
            if items:
                return items
        # Last resort: single bundled JSON
        fallback = FIXTURE_DIRS[1] / "entidades.json"
        if fallback.exists():
            return [RawItem(uri=f"file://{fallback}", meta={"kind": "fixture_fallback"})]
        return []

    def fetch(self, item: RawItem) -> bytes:
        if item.uri.startswith("file://"):
            with open(item.uri[7:], "rb") as f:
                return f.read()
        from common.http_client import assert_live_proxy_ok, request_with_retry

        assert_live_proxy_ok()
        return request_with_retry("GET", item.uri).content

    def parse(self, raw: bytes, *, source_uri: str = "") -> list[StagingRecord]:
        text = raw.decode("utf-8", errors="replace").lstrip()
        filename = source_uri.rsplit("/", 1)[-1] if source_uri else ""
        if text.startswith("{") or text.startswith("["):
            return self._parse_json(raw)
        return self._parse_tabular(raw, filename=filename)

    def _parse_tabular(self, raw: bytes, *, filename: str) -> list[StagingRecord]:
        try:
            rows = parse_file_bytes(raw, filename=filename)
        except RuntimeError:
            return []
        return [self._staging_from_dict(row) for row in rows]

    def _parse_json(self, raw: bytes) -> list[StagingRecord]:
        data = json.loads(raw.decode("utf-8", errors="replace"))
        if isinstance(data, dict) and "series" in data:
            rows = data["series"]
        else:
            rows = data if isinstance(data, list) else data.get("entidades") or data.get("data") or []
        out: list[StagingRecord] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            out.append(self._staging_from_dict(self._json_row_to_dict(row)))
        return out

    def _json_row_to_dict(self, row: dict) -> dict:
        return {
            "entity_name": row.get("entidad") or row.get("nombre") or row.get("entity"),
            "level": row.get("nivel") or "nacional",
            "year": int(row.get("gestion") or row.get("year") or 2025),
            "program_project": row.get("programa") or row.get("proyecto"),
            "budget_item": row.get("partida"),
            "department": row.get("departamento") or row.get("department"),
            "initial_amount": str(
                parse_money(row.get("presupuesto_inicial") or row.get("inicial")) or ""
            ),
            "modified_amount": str(
                parse_money(row.get("presupuesto_modificado") or row.get("modificado")) or ""
            ),
            "current_amount": str(
                parse_money(row.get("presupuesto_vigente") or row.get("vigente")) or ""
            ),
            "executed_amount": str(parse_money(row.get("ejecucion") or row.get("ejecutado")) or ""),
            "commitment": str(parse_money(row.get("compromiso") or row.get("commitment")) or ""),
            "accrual": str(parse_money(row.get("devengado") or row.get("accrual")) or ""),
            "payment": str(
                parse_money(
                    row.get("pagado")
                    or row.get("payment")
                    or row.get("ejecucion")
                    or row.get("ejecutado")
                )
                or ""
            ),
            "budget_phase": row.get("budget_phase") or "mapped",
            "source_id": self.source_id,
            "source_note": row.get("source_note") or "presupuesto_abierto_json",
        }

    def _staging_from_dict(self, row: dict) -> StagingRecord:
        return StagingRecord(
            record_type="budget",
            data={
                "entity_name": row.get("entity_name"),
                "level": row.get("level") or "nacional",
                "year": int(row.get("year") or 2025),
                "program_project": row.get("program_project"),
                "budget_item": row.get("budget_item"),
                "department": row.get("department"),
                "initial_amount": row.get("initial_amount") or "",
                "modified_amount": row.get("modified_amount") or "",
                "current_amount": row.get("current_amount") or "",
                "executed_amount": row.get("executed_amount") or "",
                "commitment": row.get("commitment") or "",
                "accrual": row.get("accrual") or "",
                "payment": row.get("payment") or "",
                "budget_phase": row.get("budget_phase") or "mapped",
                "source_id": self.source_id,
                "source_note": row.get("source_note") or "presupuesto_abierto_export",
            },
        )
