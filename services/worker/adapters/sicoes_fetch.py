from __future__ import annotations

import logging
import os
import time

from common.http_client import assert_live_proxy_ok, playwright_proxy_config
from common.rate_limit import RateLimiter

log = logging.getLogger(__name__)
_limiter = RateLimiter(float(os.getenv("SCRAPE_RATE_LIMIT_RPS", "1.0")))


class FetchError(RuntimeError):
    """Playwright fetch failed after retries (timeout, network, portal error)."""

    def __init__(self, url: str, cause: Exception, attempts: int) -> None:
        self.url = url
        self.cause = cause
        self.attempts = attempts
        super().__init__(f"fetch failed after {attempts} attempt(s) for {url}: {cause}")


def fetch_page(url: str) -> bytes:
    """Fetch a page with Playwright (live scrape), optionally via PROXY_URL.

    Retries with backoff on failure so a transient timeout does not kill the whole ingest.
    Validates non-empty HTML before returning. Raises ``FetchError`` so callers can fall
    back to offline fixtures.
    """
    assert_live_proxy_ok()
    _limiter.wait()
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import TimeoutError as PlaywrightTimeout
    from playwright.sync_api import sync_playwright

    timeout_ms = int(os.getenv("PLAYWRIGHT_TIMEOUT_MS", "60000"))
    retries = int(os.getenv("PLAYWRIGHT_RETRIES", "2"))
    min_bytes = int(os.getenv("SICOES_FETCH_MIN_BYTES", "256"))
    proxy = playwright_proxy_config()
    last_exc: Exception | None = None

    for attempt in range(max(1, retries)):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, proxy=proxy)
                try:
                    page = browser.new_page()
                    page.goto(url, wait_until="networkidle", timeout=timeout_ms)
                    html = page.content()
                finally:
                    browser.close()
            raw = html.encode("utf-8")
            if len(raw) < min_bytes:
                raise ValueError(f"response too small ({len(raw)} bytes)")
            lowered = html.lower()
            if "mantenimiento" in lowered or "servicio no disponible" in lowered:
                raise ValueError("portal maintenance page")
            if "captcha" in lowered or "recaptcha" in lowered:
                raise ValueError("captcha or bot-wall detected")
            return raw
        except (PlaywrightTimeout, PlaywrightError, OSError, ValueError) as exc:
            last_exc = exc
            kind = "timeout" if isinstance(exc, PlaywrightTimeout) else "error"
            log.warning(
                "playwright %s attempt %s/%s for %s: %s",
                kind,
                attempt + 1,
                retries,
                url,
                exc,
            )
            if attempt < retries - 1:
                backoff = float(os.getenv("SICOES_RETRY_BACKOFF_SEC", "1.5"))
                time.sleep(backoff * (attempt + 1))
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            log.warning("playwright fetch attempt %s failed for %s: %s", attempt + 1, url, exc)
            if attempt < retries - 1:
                backoff = float(os.getenv("SICOES_RETRY_BACKOFF_SEC", "1.5"))
                time.sleep(backoff * (attempt + 1))
    assert last_exc is not None
    raise FetchError(url, last_exc, max(1, retries))
