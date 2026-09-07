#!/usr/bin/env python3
"""Assert deep corpus + cross-source API look healthy."""
from __future__ import annotations

import os
import sys

import httpx

API = os.getenv("API_INTERNAL_URL") or os.getenv("API_URL") or "http://api:8000"
API = API.rstrip("/")


def main() -> None:
    urls = [API]
    if "localhost" not in API and "127.0.0.1" not in API:
        urls.append("http://localhost:8010")
    last_err = None
    for base in urls:
        try:
            stats = httpx.get(f"{base}/v1/stats", timeout=30)
            stats.raise_for_status()
            s = stats.json()
            xs = httpx.get(f"{base}/v1/cross-source/summary", timeout=30)
            xs.raise_for_status()
            x = xs.json()
            print("stats:", s)
            print("cross-source:", x)
            if s.get("contracts", 0) < 80:
                raise SystemExit(f"expected >=80 contracts, got {s.get('contracts')}")
            if x.get("cuces_multi_source", 0) < 5:
                raise SystemExit(
                    f"expected multi-source CUCEs, got {x.get('cuces_multi_source')}"
                )
            if x.get("discrepancies_total", 0) < 5:
                raise SystemExit("expected discrepancies from cross-source contrast")
            print("Deep API check OK")
            return
        except SystemExit:
            raise
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            continue
    raise SystemExit(f"deep API check failed: {last_err}")


if __name__ == "__main__":
    main()
