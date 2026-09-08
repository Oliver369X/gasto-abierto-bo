"""Startup env validation."""
from __future__ import annotations

import pytest

from common.env_validate import validate_runtime_env


def test_live_scrape_without_proxy_fails_startup(monkeypatch):
    monkeypatch.setenv("LIVE_SCRAPE", "1")
    monkeypatch.setenv("REQUIRE_PROXY_FOR_LIVE", "1")
    monkeypatch.delenv("PROXY_URL", raising=False)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    monkeypatch.delenv("HTTP_PROXY", raising=False)
    monkeypatch.delenv("ALL_PROXY", raising=False)
    with pytest.raises(RuntimeError, match="PROXY_URL"):
        validate_runtime_env()


def test_live_scrape_off_allows_startup(monkeypatch):
    monkeypatch.setenv("LIVE_SCRAPE", "0")
    monkeypatch.delenv("PROXY_URL", raising=False)
    validate_runtime_env()


def test_strict_production_rejects_loopback_cors(monkeypatch):
    monkeypatch.setenv("LIVE_SCRAPE", "0")
    monkeypatch.setenv("STRICT_PRODUCTION_ENV", "1")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3010")  # pragma: allowlist secret
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        validate_runtime_env()
