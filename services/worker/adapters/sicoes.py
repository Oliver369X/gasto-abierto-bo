from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from common.cuce import normalize_cuce
from common.dates import parse_date_flexible
from common.money import parse_money
from worker.adapters.base import Cursor, RawItem, StagingRecord
from worker.adapters.sicoes_html import (
    SicoesStructureChanged,
    inspect_list_html,
)

log = logging.getLogger(__name__)

_DEFAULT_FIXTURE = (
    Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "sicoes" / "procesos_sample.html"
)


def _offline_fallback_enabled() -> bool:
    return os.getenv("SICOES_OFFLINE_FALLBACK", "1").strip().lower() in ("1", "true", "yes")


def _fixture_fallback_path() -> Path | None:
    override = os.getenv("SICOES_FIXTURE_FALLBACK", "").strip()
    if override:
        path = Path(override)
        return path if path.exists() else None
    return _DEFAULT_FIXTURE if _DEFAULT_FIXTURE.exists() else None


def load_offline_fixture() -> bytes:
    path = _fixture_fallback_path()
    if not path:
        raise FileNotFoundError("SICOES offline fixture not found")
    return path.read_bytes()

# Spanish ficha labels → field keys
_CUCE_LABEL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "reference_price",
        re.compile(
            r"(?:monto|precio)\s+referencial\s*[:\-]?\s*([^\n<]+)",
            re.IGNORECASE,
        ),
    ),
    (
        "amount",
        re.compile(
            r"(?:monto\s+adjudicado|monto\s+del\s+contrato|monto\s+contrato|"
            r"importe\s+adjudicado)\s*[:\-]?\s*([^\n<]+)",
            re.IGNORECASE,
        ),
    ),
    (
        "supplier_name",
        re.compile(
            r"(?:proveedor|adjudicatario|empresa\s+adjudicada)\s*[:\-]?\s*([^\n<]+)",
            re.IGNORECASE,
        ),
    ),
    (
        "nit",
        re.compile(r"\bN\.?\s*I\.?\s*T\.?\s*[:\-]?\s*([0-9.\-\s]+)", re.IGNORECASE),
    ),
]


def parse_cuce_html(html: str, *, cuce: str) -> dict:
    """Extract reference_price, amount, supplier_name, nit from SICOES ficha HTML."""
    text = BeautifulSoup(html or "", "lxml").get_text("\n", strip=True)
    out: dict = {"cuce": cuce, "html": html}
    for key, pattern in _CUCE_LABEL_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        raw_val = m.group(1).strip()
        if key in ("reference_price", "amount"):
            money = parse_money(raw_val)
            if money is not None:
                out[key] = money
            else:
                out[key] = raw_val
        elif key == "nit":
            digits = re.sub(r"\D", "", raw_val)
            if digits:
                out["nit"] = digits
        else:
            # Stop at next label-ish line
            cleaned = re.split(r"[\n\r]", raw_val, maxsplit=1)[0].strip()
            if cleaned:
                out[key] = cleaned
    # Table/dl fallback: label in one cell, value in next
    if "amount" not in out or "supplier_name" not in out:
        soup = BeautifulSoup(html or "", "lxml")
        for row in soup.select("tr"):
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
            if len(cells) < 2:
                continue
            label, val = cells[0].lower(), cells[1]
            if "referencial" in label and "reference_price" not in out:
                out["reference_price"] = parse_money(val) or val
            elif ("adjudicado" in label or "monto del contrato" in label) and "amount" not in out:
                out["amount"] = parse_money(val) or val
            elif ("proveedor" in label or "adjudicatario" in label) and "supplier_name" not in out:
                out["supplier_name"] = val
            elif "nit" in label and "nit" not in out:
                digits = re.sub(r"\D", "", val)
                if digits:
                    out["nit"] = digits
    return out


class SicoesAdapter:
    """Parse SICOES HTML process listings (fixture-first, Playwright live).

    Live discover paginates beyond the first page (`SICOES_MAX_PAGES`, default 25)
    and optionally walks year filters (`SICOES_YEARS=2019,2020,...`).
    """

    source_id = "sicoes"
    list_url = "https://www.sicoes.gob.bo/contrat/procesos.php"

    def discover(self, cursor: Cursor) -> list[RawItem]:
        fixture = cursor.payload.get("fixture_path")
        if fixture:
            path = Path(fixture)
            if path.is_dir():
                # Prefer HTML pages; fall back to CSV deep corpus (avoid double ingest).
                files = sorted({*path.glob("*.html"), *path.glob("**/*.html")})
                if not files:
                    files = sorted({*path.glob("*.csv"), *path.glob("**/*.csv")})
                return [
                    RawItem(uri=f"file://{p}", meta={"page": i + 1})
                    for i, p in enumerate(files)
                ]
            return [RawItem(uri=f"file://{path}", meta={"page": 1})]

        max_pages = int(
            cursor.payload.get("max_pages")
            or os.getenv("SICOES_MAX_PAGES", "25")
        )
        years_raw = cursor.payload.get("years") or os.getenv("SICOES_YEARS", "")
        years = [
            y.strip()
            for y in str(years_raw).split(",")
            if y.strip().isdigit()
        ]

        items: list[RawItem] = []
        if years:
            for year in years:
                for p in range(1, max_pages + 1):
                    items.append(
                        RawItem(
                            uri=f"{self.list_url}?gestion={year}&page={p}",
                            meta={"page": p, "year": int(year)},
                        )
                    )
        else:
            for p in range(1, max_pages + 1):
                items.append(
                    RawItem(uri=f"{self.list_url}?page={p}", meta={"page": p})
                )
        return items

    def fetch(self, item: RawItem) -> bytes:
        if item.uri.startswith("file://"):
            with open(item.uri[7:], "rb") as f:
                return f.read()
        from worker.adapters.sicoes_fetch import FetchError, fetch_page

        try:
            return fetch_page(item.uri)
        except FetchError as exc:
            if _offline_fallback_enabled():
                log.warning("SICOES live fetch failed (%s); using offline fixture", exc)
                return load_offline_fixture()
            raise

    def parse(self, raw: bytes) -> list[StagingRecord]:
        # CSV fixtures used for deep/cross-source seeds
        text_head = raw[:200].lstrip()
        if text_head.startswith(b"cuce,") or b"\ncuce," in raw[:500].lower():
            return self._parse_csv(raw)

        inspection = inspect_list_html(raw)
        if not inspection.parseable:
            log.warning(
                "SICOES HTML structure issue [%s]: %s",
                inspection.marker,
                inspection.reason,
            )
            if _offline_fallback_enabled():
                fallback = _fixture_fallback_path()
                if fallback and fallback.read_bytes() != raw:
                    log.warning("SICOES parse fallback → %s", fallback)
                    return self.parse(fallback.read_bytes())
            raise SicoesStructureChanged(inspection)

        soup = BeautifulSoup(raw, "lxml")
        table = soup.select_one("table.resultados") or soup.select_one("table")
        if not table:
            return []

        headers = [
            th.get_text(" ", strip=True).lower()
            for th in table.select("tr th")
        ]
        out: list[StagingRecord] = []
        for tr in table.select("tr")[1:]:
            cols = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if len(cols) < 5:
                continue
            mapped = self._map_row(headers, cols)
            docs = []
            for a in tr.select("a[href]"):
                href = a.get("href") or ""
                if href:
                    docs.append(urljoin(self.list_url, href))
            out.append(
                StagingRecord(
                    record_type="contract",
                    data={
                        **mapped,
                        "documents": docs,
                        "source_id": self.source_id,
                    },
                )
            )
        return out

    def _parse_csv(self, raw: bytes) -> list[StagingRecord]:
        import csv
        import io

        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig", errors="replace")))
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
                        or row.get("entidad")
                        or "Entidad SICOES",
                        "supplier_name": row.get("supplier") or row.get("proveedor"),
                        "object_description": row.get("description")
                        or row.get("objeto")
                        or row.get("title"),
                        "amount": row.get("amount") or row.get("monto"),
                        "modality": row.get("modality") or row.get("modalidad"),
                        "contract_date": row.get("date") or row.get("fecha"),
                        "status": row.get("status") or row.get("estado"),
                        "department": row.get("department") or row.get("departamento"),
                        "source_id": self.source_id,
                        "source_note": row.get("source_note")
                        or row.get("fuente")
                        or "sicoes_csv_mirror",
                    },
                )
            )
        return out

    def _map_row(self, headers: list[str], cols: list[str]) -> dict:
        def col(*names: str) -> str | None:
            for i, h in enumerate(headers):
                if any(n in h for n in names) and i < len(cols):
                    return cols[i] or None
            return None

        cuce = normalize_cuce(
            col("cuce") or (cols[1] if len(cols) > 1 else None)
        )
        entity = col("responsable", "entidad") or (cols[2] if len(cols) > 2 else None)
        modality = col("modalidad") or (cols[3] if len(cols) > 3 else None)
        objeto = col("objeto")
        status = col("estado")
        fecha = col("fecha")
        proveedor = col("proveedor", "adjudicatario", "empresa")
        monto_raw = col("monto", "importe", "precio", "valor")

        if not objeto:
            objeto = max(cols, key=len) if cols else None
        if not fecha:
            for c in cols:
                if parse_date_flexible(c):
                    fecha = c
                    break
        if not monto_raw:
            for c in cols:
                if re.search(r"\d+[.,]\d{2}$", c) or re.search(r"^\d{1,3}([.,]\d{3})+", c):
                    if parse_money(c) and parse_money(c) > 100:
                        monto_raw = c
                        break
        if not status and len(cols) >= 8:
            status = cols[7]

        return {
            "cuce": cuce,
            "entity_name": entity or "Entidad SICOES",
            "supplier_name": proveedor,
            "object_description": objeto,
            "modality": modality,
            "amount": monto_raw,
            "contract_date": fecha,
            "status": status,
            "source_note": "sicoes_html_table",
        }

    def fetch_cuce_detail(self, cuce: str) -> dict | None:
        """Fetch CUCE ficha HTML via Playwright when PROXY_URL is set; else None.

        When HTML is retrieved, always runs through ``parse_cuce_html``.
        """
        cuce = (cuce or "").strip()
        if not cuce:
            return None
        proxy = os.getenv("PROXY_URL", "").strip()
        if not proxy:
            return None
        url = (
            f"https://www.sicoes.gob.bo/portal/contrataciones/consulta/"
            f"busqueda_avance.php?cuce={cuce}"
        )
        from worker.adapters.sicoes_fetch import fetch_page

        raw = fetch_page(url)
        html = raw.decode("utf-8", errors="replace")
        detail = parse_cuce_html(html, cuce=cuce)
        detail["url"] = url
        detail["source_note"] = "sicoes_live_ficha"
        return detail
