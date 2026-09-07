"""Download official Presupuesto Abierto CSV/Parquet exports.

Prefer direct file URLs from https://abierto.economiayfinanzas.gob.bo/descargas
over scraping the SPA portal.

Configure with comma-separated env var PRESUPUESTO_ABIERTO_DOWNLOAD_URLS or pass
explicit URLs to fetch_presupuesto().
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Iterable

import httpx

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "tests" / "fixtures" / "real" / "presupuesto_abierto"
UA = "GastoAbiertoBO/0.8 (+research; open-data; presupuesto-abierto)"

# Placeholder patterns — replace with URLs copied from the official /descargas page.
# These are documented defaults; live URLs vary by release.
DOCUMENTED_DOWNLOADS: list[tuple[str, str]] = [
    (
        "presupuesto_historico.csv",
        "https://abierto.economiayfinanzas.gob.bo/descargas",
    ),
]


def list_download_urls() -> list[str]:
    env = os.getenv("PRESUPUESTO_ABIERTO_DOWNLOAD_URLS", "").strip()
    if env:
        return [u.strip() for u in env.split(",") if u.strip()]
    return [url for _, url in DOCUMENTED_DOWNLOADS]


def _client() -> httpx.Client:
    return httpx.Client(timeout=300, follow_redirects=True, headers={"User-Agent": UA})


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
                print("  skip HTML response (not a data file — copy direct URL from /descargas)")
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


def fetch_presupuesto(
    dest: Path | None = None,
    *,
    urls: Iterable[str] | None = None,
    force: bool = False,
) -> list[Path]:
    """Download configured URLs into dest. Returns successfully written paths."""
    out_dir = dest or DEFAULT_OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    target_urls = list(urls) if urls is not None else list_download_urls()
    wrote: list[Path] = []
    meta: dict = {"downloads": [], "dest": str(out_dir)}
    with _client() as c:
        for i, url in enumerate(target_urls):
            fname = _safe_name(url, i)
            path = out_dir / fname
            ok = _download(c, url, path, force=force)
            meta["downloads"].append({"url": url, "ok": ok, "path": str(path)})
            if ok:
                wrote.append(path)
    manifest = out_dir.parent / "presupuesto_download_manifest.json"
    manifest.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return wrote
