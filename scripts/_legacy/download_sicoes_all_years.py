#!/usr/bin/env python3
"""Download ALL SICOES convocatorias by month (2007→hoy) from sociedatos + lab.

Sources (civic mirrors of SICOES, multi-gestión — not a single year):
  - https://github.com/sociedatos/bo-convocatorias_publicas  (mensual YYYYMM.csv)
  - https://github.com/lab-tecnosocial/datos-sicoes         (todo.csv consolidado)

  python scripts/download_sicoes_all_years.py
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "real" / "sicoes_history"
OUT.mkdir(parents=True, exist_ok=True)

UA = "GastoAbiertoBO/0.7 (+research; SICOES history mirror)"
BASE = "https://raw.githubusercontent.com/sociedatos/bo-convocatorias_publicas/master/data"
LAB_TODO = "https://raw.githubusercontent.com/lab-tecnosocial/datos-sicoes/main/todo/todo.csv"
API = "https://api.github.com/repos/sociedatos/bo-convocatorias_publicas/contents/data"


def list_months(client: httpx.Client) -> list[str]:
    r = client.get(API, headers={"Accept": "application/vnd.github+json"})
    r.raise_for_status()
    names = []
    for it in r.json():
        m = re.fullmatch(r"(\d{6})\.csv", it.get("name") or "")
        if m:
            names.append(m.group(1))
    return sorted(names)


def fetch_one(client: httpx.Client, yyyymm: str) -> dict:
    dest = OUT / "months" / f"{yyyymm}.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1000:
        return {"month": yyyymm, "ok": True, "bytes": dest.stat().st_size, "cached": True}
    url = f"{BASE}/{yyyymm}.csv"
    try:
        with client.stream("GET", url) as r:
            if r.status_code >= 400:
                return {"month": yyyymm, "ok": False, "status": r.status_code}
            tmp = dest.with_suffix(".part")
            n = 0
            with tmp.open("wb") as f:
                for chunk in r.iter_bytes(1 << 16):
                    f.write(chunk)
                    n += len(chunk)
            tmp.replace(dest)
        return {"month": yyyymm, "ok": True, "bytes": n, "cached": False}
    except Exception as exc:  # noqa: BLE001
        return {"month": yyyymm, "ok": False, "error": str(exc)}


def fetch_lab(client: httpx.Client) -> dict:
    dest = OUT / "lab_todo.csv"
    if dest.exists() and dest.stat().st_size > 1_000_000:
        return {"ok": True, "bytes": dest.stat().st_size, "cached": True, "path": str(dest)}
    try:
        with client.stream("GET", LAB_TODO) as r:
            r.raise_for_status()
            tmp = dest.with_suffix(".part")
            n = 0
            with tmp.open("wb") as f:
                for chunk in r.iter_bytes(1 << 16):
                    f.write(chunk)
                    n += len(chunk)
            tmp.replace(dest)
        return {"ok": True, "bytes": n, "cached": False, "path": str(dest)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def main() -> None:
    client = httpx.Client(timeout=180, follow_redirects=True, headers={"User-Agent": UA})
    months = list_months(client)
    # Prefer full span; if API rate-limits, generate 200711→current
    if len(months) < 50:
        start = datetime(2007, 11, 1)
        end = datetime.utcnow()
        months = []
        y, m = start.year, start.month
        while (y, m) <= (end.year, end.month):
            months.append(f"{y}{m:02d}")
            m += 1
            if m > 12:
                m = 1
                y += 1

    print(f"months to fetch: {len(months)} ({months[0]}..{months[-1]})")
    results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(fetch_one, client, ym) for ym in months]
        for i, fut in enumerate(as_completed(futs), 1):
            res = fut.result()
            results.append(res)
            if i % 20 == 0 or not res.get("ok"):
                print(i, res)

    lab = fetch_lab(client)
    print("lab_todo", lab)

    ok = [r for r in results if r.get("ok")]
    manifest = {
        "months_ok": len(ok),
        "months_total": len(months),
        "bytes": sum(r.get("bytes") or 0 for r in ok),
        "lab": lab,
        "span": [months[0], months[-1]] if months else [],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    if len(ok) < 100:
        raise SystemExit("too few monthly files downloaded")


if __name__ == "__main__":
    main()
