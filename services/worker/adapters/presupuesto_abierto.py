from __future__ import annotations

import json
import os
from pathlib import Path

from common.money import parse_money
from worker.adapters.base import Cursor, RawItem, StagingRecord


class PresupuestoAbiertoAdapter:
    """Parse Presupuesto Abierto JSON payloads (XHR captures / fixtures).

    Offline: accepts a file or a directory of JSON dumps (full history).
    Live: walks configured endpoint list (`PRESUPUESTO_ABIERTO_URLS`) with soft-fail.
    """

    source_id = "presupuesto_abierto"
    default_live_urls = (
        "https://abierto.economiayfinanzas.gob.bo/",
    )

    def discover(self, cursor: Cursor) -> list[RawItem]:
        fixture = cursor.payload.get("fixture_path")
        if fixture:
            path = Path(fixture)
            if path.is_dir():
                files = sorted({*path.glob("*.json"), *path.glob("**/*.json")})
                return [RawItem(uri=f"file://{p}", meta={"kind": "fixture"}) for p in files]
            return [RawItem(uri=f"file://{path}", meta={})]

        env_urls = os.getenv("PRESUPUESTO_ABIERTO_URLS", "").strip()
        urls = (
            [u.strip() for u in env_urls.split(",") if u.strip()]
            if env_urls
            else list(self.default_live_urls)
        )
        # Optional captured XHR endpoints (JSON) — same env, comma-separated
        return [
            RawItem(uri=u, meta={"note": "live; prefer JSON XHR captures"})
            for u in urls
        ]

    def fetch(self, item: RawItem) -> bytes:
        if item.uri.startswith("file://"):
            with open(item.uri[7:], "rb") as f:
                return f.read()
        from common.http_client import assert_live_proxy_ok, request_with_retry

        assert_live_proxy_ok()
        return request_with_retry("GET", item.uri).content

    def parse(self, raw: bytes) -> list[StagingRecord]:
        text = raw.decode("utf-8", errors="replace").lstrip()
        if not text.startswith("{") and not text.startswith("["):
            # HTML homepage is not useful as budget rows — skip quietly
            return []
        data = json.loads(text)
        if isinstance(data, dict) and "series" in data:
            rows = data["series"]
        else:
            rows = data if isinstance(data, list) else data.get("entidades") or data.get("data") or []
        out: list[StagingRecord] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            out.append(
                StagingRecord(
                    record_type="budget",
                    data={
                        "entity_name": row.get("entidad")
                        or row.get("nombre")
                        or row.get("entity"),
                        "level": row.get("nivel") or "nacional",
                        "year": int(row.get("gestion") or row.get("year") or 2025),
                        "program_project": row.get("programa") or row.get("proyecto"),
                        "budget_item": row.get("partida"),
                        "department": row.get("departamento") or row.get("department"),
                        "initial_amount": str(
                            parse_money(
                                row.get("presupuesto_inicial") or row.get("inicial")
                            )
                            or ""
                        ),
                        "modified_amount": str(
                            parse_money(
                                row.get("presupuesto_modificado") or row.get("modificado")
                            )
                            or ""
                        ),
                        "current_amount": str(
                            parse_money(
                                row.get("presupuesto_vigente") or row.get("vigente")
                            )
                            or ""
                        ),
                        "executed_amount": str(
                            parse_money(row.get("ejecucion") or row.get("ejecutado")) or ""
                        ),
                        "commitment": str(
                            parse_money(row.get("compromiso") or row.get("commitment")) or ""
                        ),
                        "accrual": str(
                            parse_money(row.get("devengado") or row.get("accrual")) or ""
                        ),
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
                    },
                )
            )
        return out
