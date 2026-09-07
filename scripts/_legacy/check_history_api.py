#!/usr/bin/env python3
"""Smoke-check history + proxy status against the running API service."""
from __future__ import annotations

import os
import sys

import httpx

API = os.getenv("API_INTERNAL_URL", "http://api:8000")


def main() -> None:
    r = httpx.get(f"{API}/v1/history/years", timeout=30)
    r.raise_for_status()
    years = r.json()
    assert years, "expected historical years"
    assert any(y["year"] <= 2020 for y in years), years
    print("history years:", [y["year"] for y in years])
    s = httpx.get(f"{API}/v1/stats", timeout=30).json()
    print("stats:", s)
    h = httpx.get(f"{API}/v1/health", timeout=30).json()
    print("proxy status:", h.get("proxy"))
    assert "proxy_configured" in (h.get("proxy") or {})
    sr = httpx.get(f"{API}/v1/search", params={"q": "Andes"}, timeout=30)
    sr.raise_for_status()
    print("search hits:", len(sr.json().get("hits") or []))
    cmp = httpx.get(
        f"{API}/v1/history/compare",
        params={"year_a": 2024, "year_b": 2025},
        timeout=30,
    )
    cmp.raise_for_status()
    print("compare:", cmp.json())
    disc = httpx.get(f"{API}/v1/discrepancies", params={"limit": 5}, timeout=30)
    disc.raise_for_status()
    print("discrepancies sample:", len(disc.json()))
    print("OK")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("FAIL:", exc, file=sys.stderr)
        sys.exit(1)
