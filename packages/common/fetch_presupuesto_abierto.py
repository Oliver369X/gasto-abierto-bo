"""Download official Presupuesto Abierto CSV/Parquet exports.

Prefer direct file URLs from https://abierto.economiayfinanzas.gob.bo/descargas
over scraping the SPA portal.

Configure with comma-separated env var PRESUPUESTO_ABIERTO_DOWNLOAD_URLS or pass
explicit URLs to fetch_presupuesto(). When env is empty, we discover URLs from
the official /descargas page (developer Parquet links + CSV patterns) and fall
back to bundled fixtures for offline/dev use.
"""
from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "tests" / "fixtures" / "real" / "presupuesto_abierto"
FIXTURE_SRC = ROOT / "tests" / "fixtures" / "presupuesto_abierto"
UA = "GastoAbiertoBO/0.8 (+research; open-data; presupuesto-abierto)"
DESCARGAS_PAGE = "https://abierto.economiayfinanzas.gob.bo/descargas"
BASE_HOST = "https://abierto.economiayfinanzas.gob.bo"

# Documented developer Parquet endpoints (stable programmatic URLs).
DOCUMENTED_DOWNLOADS: list[tuple[str, str]] = [
    (
        "gasto.parquet",
        f"{BASE_HOST}/presupuesto/descargas/gasto/ultimo/gasto.parquet",
    ),
    (
        "ingreso.parquet",
        f"{BASE_HOST}/presupuesto/descargas/ingreso/ultimo/ingreso.parquet",
    ),
]

_DATA_EXT = (".csv", ".parquet", ".zip", ".xlsx")


def _client() -> httpx.Client:
    return httpx.Client(timeout=300, follow_redirects=True, headers={"User-Agent": UA})


def _normalize_url(href: str) -> str | None:
    href = (href or "").strip()
    if not href or href.startswith("#") or href.startswith("javascript:"):
        return None
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return urljoin(BASE_HOST, href)
    return None


def _looks_like_data_url(url: str) -> bool:
    lower = url.lower().split("?", 1)[0]
    return any(lower.endswith(ext) for ext in _DATA_EXT) or "/descargas/" in lower


def discover_download_urls(*, fetch_page: bool = True) -> list[str]:
    """Discover direct download URLs from the official /descargas page."""
    seen: set[str] = set()
    urls: list[str] = []

    def add(u: str | None) -> None:
        if not u or u in seen:
            return
        if not _looks_like_data_url(u):
            return
        seen.add(u)
        urls.append(u)

    for _, url in DOCUMENTED_DOWNLOADS:
        add(url)

    if not fetch_page:
        return urls

    try:
        with _client() as c:
            r = c.get(DESCARGAS_PAGE)
            if r.status_code >= 400:
                return urls
            html = r.text
    except Exception:  # noqa: BLE001
        return urls

    # Absolute URLs in page source (developer section uses backtick-wrapped URLs).
    for match in re.finditer(r"https?://[^\s`'\"<>]+\.(?:csv|parquet|zip|xlsx)", html, re.I):
        add(match.group(0).rstrip(".,;)"))

    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(["a", "link"], href=True):
        add(_normalize_url(tag["href"]))

    # Relative presupuesto paths sometimes appear without scheme.
    for match in re.finditer(
        r"(/presupuesto/descargas/[^\s`'\"<>]+\.(?:csv|parquet|zip|xlsx))",
        html,
        re.I,
    ):
        add(urljoin(BASE_HOST, match.group(1)))

    return urls


def list_download_urls(*, discover: bool = True) -> list[str]:
    """Return URLs to download: env override, then discovered, then documented."""
    env = os.getenv("PRESUPUESTO_ABIERTO_DOWNLOAD_URLS", "").strip()
    if not env:
        env = os.getenv("PRESUPUESTO_ABIERTO_URLS", "").strip()
    if env:
        return [u.strip() for u in env.split(",") if u.strip()]
    discovered = discover_download_urls(fetch_page=discover)
    if discovered:
        return discovered
    return [url for _, url in DOCUMENTED_DOWNLOADS]


def _safe_name(url: str, index: int) -> str:
    tail = url.rstrip("/").split("/")[-1] or f"download_{index}"
    tail = re.sub(r"[^\w.\-]+", "_", tail)[:120]
    if not Path(tail).suffix:
        tail += ".csv"
    return tail


def _download(c: httpx.Client, url: str, dest: Path, *, force: bool) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 100 and not force:
        return True
    print(f"GET {url}")
    try:
        with c.stream("GET", url) as r:
            if r.status_code >= 400:
                print(f"  skip HTTP {r.status_code}")
                return False
            ctype = (r.headers.get("content-type") or "").lower()
            if "text/html" in ctype and dest.suffix in (".csv", ".parquet"):
                print("  skip HTML response (not a data file — use direct URL from /descargas)")
                return False
            tmp = dest.with_suffix(dest.suffix + ".part")
            with tmp.open("wb") as f:
                for chunk in r.iter_bytes(1 << 16):
                    f.write(chunk)
            tmp.replace(dest)
        print(f"  -> {dest} ({dest.stat().st_size} bytes)")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL {exc}")
        return False


def copy_fixture_fallback(dest: Path) -> list[Path]:
    """Copy bundled CSV/JSON fixtures when live download is unavailable."""
    dest.mkdir(parents=True, exist_ok=True)
    wrote: list[Path] = []
    if not FIXTURE_SRC.exists():
        return wrote
    for src in sorted(FIXTURE_SRC.rglob("*")):
        if not src.is_file():
            continue
        if src.suffix.lower() not in (".csv", ".json", ".parquet"):
            continue
        target = dest / src.name
        if target.exists() and target.stat().st_size > 0:
            wrote.append(target)
            continue
        shutil.copy2(src, target)
        print(f"  fixture -> {target}")
        wrote.append(target)
    return wrote


def fetch_presupuesto(
    dest: Path | None = None,
    *,
    urls: Iterable[str] | None = None,
    force: bool = False,
    allow_fixture_fallback: bool = True,
    live: bool | None = None,
) -> list[Path]:
    """Download configured URLs into dest. Returns successfully written paths."""
    out_dir = dest or DEFAULT_OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    target_urls = list(urls) if urls is not None else list_download_urls()
    if live is None:
        live = os.getenv("LIVE_SCRAPE", "0") == "1"
    if live and any(u.startswith(("http://", "https://")) for u in target_urls):
        from common.http_client import assert_live_proxy_ok

        assert_live_proxy_ok()
    wrote: list[Path] = []
    meta: dict = {"downloads": [], "dest": str(out_dir), "fixture_fallback": False}
    with _client() as c:
        for i, url in enumerate(target_urls):
            fname = _safe_name(url, i)
            path = out_dir / fname
            ok = _download(c, url, path, force=force)
            meta["downloads"].append({"url": url, "ok": ok, "path": str(path)})
            if ok:
                wrote.append(path)

    if not wrote and allow_fixture_fallback:
        fixture_paths = copy_fixture_fallback(out_dir)
        if fixture_paths:
            meta["fixture_fallback"] = True
            meta["fixture_paths"] = [str(p) for p in fixture_paths]
            wrote = fixture_paths

    manifest = out_dir.parent / "presupuesto_download_manifest.json"
    manifest.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return wrote
