"""Regression: browser download/CSV links must not hardcode loopback hosts."""
from __future__ import annotations

import re
from pathlib import Path

WEB_ROOT = Path(__file__).resolve().parents[1] / "services" / "web"
_LOOPBACK_HOST = "loc" + "alhost"
LOOPBACK = re.compile(
    rf"https?://(?:{_LOOPBACK_HOST}|127\.0\.0\.1)(?::|\b)",
    re.I,
)
API_BASE_DOWNLOAD = re.compile(r"\$\{api\}/v1/(?:documents|fire/export\.csv)")


def _iter_source_files() -> list[Path]:
    return sorted(WEB_ROOT.rglob("*"))


def test_web_sources_have_no_loopback_download_urls():
    offenders: list[str] = []
    for path in _iter_source_files():
        if path.suffix not in {".ts", ".tsx", ".js", ".jsx"}:
            continue
        text = path.read_text(encoding="utf-8")
        for match in LOOPBACK.finditer(text):
            offenders.append(f"{path.relative_to(WEB_ROOT)}:{match.group(0)}")
    assert not offenders, "loopback URLs in web sources:\n" + "\n".join(offenders)


def test_web_document_and_csv_links_use_api_public_url():
    offenders: list[str] = []
    for path in _iter_source_files():
        if path.suffix not in {".tsx", ".jsx"}:
            continue
        text = path.read_text(encoding="utf-8")
        if API_BASE_DOWNLOAD.search(text):
            offenders.append(str(path.relative_to(WEB_ROOT)))
    assert not offenders, "use apiPublicUrl() for browser downloads:\n" + "\n".join(offenders)
