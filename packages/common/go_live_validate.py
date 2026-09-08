"""Go-live environment and readiness checks (Wave 6)."""
from __future__ import annotations

import os
import sys
from urllib.parse import urlparse

from common.http_client import assert_live_proxy_ok

_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "0.0.0.0"})  # pragma: allowlist secret


def is_loopback_url(url: str | None) -> bool:
    raw = (url or "").strip()
    if not raw:
        return False
    try:
        host = (urlparse(raw).hostname or "").lower()
    except ValueError:
        return False
    if host in _LOOPBACK_HOSTS:
        return True
    if host.startswith("127."):
        return True
    return False


def presupuesto_urls_configured() -> bool:
    for key in ("PRESUPUESTO_ABIERTO_DOWNLOAD_URLS", "PRESUPUESTO_ABIERTO_URLS"):
        if (os.getenv(key) or "").strip():
            return True
    return False


def validate_go_live_env() -> None:
    """Fail loud when production env is misconfigured."""
    api_url = (os.getenv("NEXT_PUBLIC_API_URL") or "").strip()
    if not api_url:
        raise RuntimeError("NEXT_PUBLIC_API_URL must be set for go-live")
    if is_loopback_url(api_url):
        raise RuntimeError(
            f"NEXT_PUBLIC_API_URL must not point to loopback in go-live (got {api_url!r})"
        )

    assert_live_proxy_ok()

    if not presupuesto_urls_configured():
        raise RuntimeError(
            "PRESUPUESTO_ABIERTO_DOWNLOAD_URLS (or PRESUPUESTO_ABIERTO_URLS) must be set for go-live"
        )


def main() -> int:
    try:
        validate_go_live_env()
    except RuntimeError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
