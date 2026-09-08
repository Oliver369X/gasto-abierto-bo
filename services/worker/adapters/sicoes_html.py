"""SICOES HTML structure inspection — detect layout changes before parse fails silently."""
from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class SicoesHtmlInspection:
    parseable: bool
    marker: str
    reason: str
    row_count: int = 0


class SicoesStructureChanged(Exception):
    """Raised when SICOES list HTML no longer matches expected layout markers."""

    def __init__(self, inspection: SicoesHtmlInspection) -> None:
        self.inspection = inspection
        super().__init__(inspection.reason)


def inspect_list_html(raw: bytes) -> SicoesHtmlInspection:
    """Check whether SICOES process-list HTML is parseable with current selectors."""
    text = raw.decode("utf-8", errors="replace")
    lowered = text.lower()

    if not text.strip():
        return SicoesHtmlInspection(False, "empty", "empty response body")

    if "mantenimiento" in lowered or "servicio no disponible" in lowered:
        return SicoesHtmlInspection(False, "maintenance", "portal maintenance page detected")

    if "captcha" in lowered or "recaptcha" in lowered:
        return SicoesHtmlInspection(False, "captcha", "captcha or bot-wall detected")

    soup = BeautifulSoup(raw, "lxml")
    table = soup.select_one("table.resultados") or soup.select_one("table")
    if not table:
        return SicoesHtmlInspection(False, "no_table", "no results table found in HTML")

    headers = [th.get_text(" ", strip=True).lower() for th in table.select("tr th")]
    header_blob = " ".join(headers)
    has_cuce = "cuce" in header_blob or bool(re.search(r"\bcuce\b", lowered[:8000]))
    rows = table.select("tr")[1:]
    data_rows = [tr for tr in rows if tr.find_all("td")]

    if not data_rows and not has_cuce:
        return SicoesHtmlInspection(
            False,
            "no_rows",
            "table present but no data rows and no CUCE column marker",
        )

    if not data_rows and has_cuce:
        return SicoesHtmlInspection(True, "table.resultados", "empty result set (valid layout)", 0)

    return SicoesHtmlInspection(
        True,
        "table.resultados" if soup.select_one("table.resultados") else "table",
        "ok",
        len(data_rows),
    )


def assert_list_html_parseable(raw: bytes) -> SicoesHtmlInspection:
    inspection = inspect_list_html(raw)
    if not inspection.parseable:
        raise SicoesStructureChanged(inspection)
    return inspection
