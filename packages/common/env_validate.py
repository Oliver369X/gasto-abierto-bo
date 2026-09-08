"""Runtime environment guards — fail loud at process startup."""
from __future__ import annotations

import os
import sys

from common.http_client import assert_live_proxy_ok

_LOOPBACK = ("localhost", "127.0.0.1")  # pragma: allowlist secret


def validate_runtime_env() -> None:
    """Refuse startup when LIVE_SCRAPE=1 without a configured proxy."""
    assert_live_proxy_ok()
    if os.getenv("STRICT_PRODUCTION_ENV", "0") != "1":
        return
    for key in ("NEXT_PUBLIC_API_URL", "CORS_ORIGINS"):
        val = (os.getenv(key) or "").lower()
        if any(tok in val for tok in _LOOPBACK):
            raise RuntimeError(
                f"{key} must not point to loopback in production (got {os.getenv(key)!r})"
            )


def main() -> int:
    try:
        validate_runtime_env()
    except RuntimeError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
