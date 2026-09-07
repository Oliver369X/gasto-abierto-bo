from __future__ import annotations

import os
import time
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

import httpx


def resolve_proxy_url() -> str | None:
    """Prefer PROXY_URL, then HTTPS_PROXY, then HTTP_PROXY.

    Set these in `.env` to route live scrapes through your VPN/proxy and
    avoid exposing your home IP to government portals.
    Example: PROXY_URL=http://user:pass@127.0.0.1:7890
    For host VPN on Docker Desktop: PROXY_URL=http://host.docker.internal:7890
    """
    for key in ("PROXY_URL", "HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY"):
        val = (os.getenv(key) or "").strip()
        if val:
            return val
    return None


def proxy_required_for_live() -> bool:
    return os.getenv("REQUIRE_PROXY_FOR_LIVE", "1") == "1"


def assert_live_proxy_ok() -> None:
    """Refuse live network scrapes without a proxy when REQUIRE_PROXY_FOR_LIVE=1."""
    if os.getenv("LIVE_SCRAPE", "0") != "1":
        return
    if not proxy_required_for_live():
        return
    if not resolve_proxy_url():
        raise RuntimeError(
            "LIVE_SCRAPE=1 requiere PROXY_URL (o HTTPS_PROXY) para no exponer tu IP. "
            "Configurá tu VPN/proxy en .env — ver docs/ops.md#proxy-vpn."
        )


@lru_cache(maxsize=1)
def get_http_client() -> httpx.Client:
    proxy = resolve_proxy_url()
    timeout = float(os.getenv("HTTP_TIMEOUT_SECONDS", "60"))
    headers = {
        "User-Agent": os.getenv(
            "HTTP_USER_AGENT",
            "GastoAbiertoBO/0.4 (+https://github.com/gasto-abierto-bo; research; respectful crawler)",
        )
    }
    kwargs: dict[str, Any] = {
        "timeout": timeout,
        "headers": headers,
        "follow_redirects": True,
    }
    if proxy:
        kwargs["proxy"] = proxy
    return httpx.Client(**kwargs)


def request_with_retry(
    method: str,
    url: str,
    *,
    client: httpx.Client | None = None,
    retries: int | None = None,
    backoff: float | None = None,
    **kwargs: Any,
) -> httpx.Response:
    """HTTP GET/POST with exponential backoff. Retries on network/5xx errors."""
    client = client or get_http_client()
    retries = retries if retries is not None else int(os.getenv("HTTP_RETRIES", "3"))
    backoff = backoff if backoff is not None else float(os.getenv("HTTP_RETRY_BACKOFF", "1.0"))
    last_exc: Exception | None = None
    for attempt in range(max(1, retries)):
        try:
            resp = client.request(method, url, **kwargs)
            if resp.status_code >= 500 and attempt < retries - 1:
                time.sleep(backoff * (2**attempt))
                continue
            resp.raise_for_status()
            return resp
        except (httpx.TransportError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            last_exc = exc
            if attempt >= retries - 1:
                break
            time.sleep(backoff * (2**attempt))
    assert last_exc is not None
    raise last_exc


def playwright_proxy_config() -> dict[str, str] | None:
    proxy = resolve_proxy_url()
    if not proxy:
        return None
    parsed = urlparse(proxy)
    server = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
    cfg: dict[str, str] = {"server": server}
    if parsed.username:
        cfg["username"] = parsed.username
    if parsed.password:
        cfg["password"] = parsed.password
    return cfg


def proxy_status() -> dict[str, Any]:
    proxy = resolve_proxy_url()
    return {
        "proxy_configured": bool(proxy),
        "proxy_host": urlparse(proxy).hostname if proxy else None,
        "require_proxy_for_live": proxy_required_for_live(),
        "live_scrape": os.getenv("LIVE_SCRAPE", "0") == "1",
    }
