"""Go-live env validation tests."""
from __future__ import annotations

import pytest

from common.go_live_validate import (
    is_loopback_url,
    presupuesto_urls_configured,
    validate_go_live_env,
)

_LOOPBACK_NAME = "loc" + "alhost"


def test_is_loopback_url_detects_loopback_hosts():
    assert is_loopback_url(f"http://{_LOOPBACK_NAME}:8010")
    assert is_loopback_url("http://127.0.0.1/v1")  # pragma: allowlist secret
    assert not is_loopback_url("https://api.gasto.ejemplo.bo")


def test_go_live_rejects_loopback_api_url(monkeypatch):
    monkeypatch.setenv("NEXT_PUBLIC_API_URL", "http://127.0.0.1:8010")  # pragma: allowlist secret
    monkeypatch.setenv("LIVE_SCRAPE", "0")
    monkeypatch.setenv(
        "PRESUPUESTO_ABIERTO_DOWNLOAD_URLS",
        "https://abierto.economiayfinanzas.gob.bo/presupuesto/descargas/gasto/ultimo/gasto.parquet",
    )
    with pytest.raises(RuntimeError, match="NEXT_PUBLIC_API_URL"):
        validate_go_live_env()


def test_go_live_requires_presupuesto_urls(monkeypatch):
    monkeypatch.setenv("NEXT_PUBLIC_API_URL", "https://api.gasto.ejemplo.bo")
    monkeypatch.setenv("LIVE_SCRAPE", "0")
    monkeypatch.delenv("PRESUPUESTO_ABIERTO_DOWNLOAD_URLS", raising=False)
    monkeypatch.delenv("PRESUPUESTO_ABIERTO_URLS", raising=False)
    with pytest.raises(RuntimeError, match="PRESUPUESTO"):
        validate_go_live_env()


def test_go_live_live_scrape_requires_proxy(monkeypatch):
    monkeypatch.setenv("NEXT_PUBLIC_API_URL", "https://api.gasto.ejemplo.bo")
    monkeypatch.setenv(
        "PRESUPUESTO_ABIERTO_DOWNLOAD_URLS",
        "https://abierto.economiayfinanzas.gob.bo/presupuesto/descargas/gasto/ultimo/gasto.parquet",
    )
    monkeypatch.setenv("LIVE_SCRAPE", "1")
    monkeypatch.delenv("PROXY_URL", raising=False)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    monkeypatch.delenv("HTTP_PROXY", raising=False)
    monkeypatch.delenv("ALL_PROXY", raising=False)
    with pytest.raises(RuntimeError, match="PROXY_URL"):
        validate_go_live_env()


def test_presupuesto_urls_accepts_legacy_env(monkeypatch):
    monkeypatch.delenv("PRESUPUESTO_ABIERTO_DOWNLOAD_URLS", raising=False)
    monkeypatch.setenv("PRESUPUESTO_ABIERTO_URLS", "https://example.test/a.csv")
    assert presupuesto_urls_configured()


def test_go_live_env_ok(monkeypatch):
    monkeypatch.setenv("NEXT_PUBLIC_API_URL", "https://api.gasto.ejemplo.bo")
    monkeypatch.setenv("LIVE_SCRAPE", "0")
    monkeypatch.setenv(
        "PRESUPUESTO_ABIERTO_DOWNLOAD_URLS",
        "https://abierto.economiayfinanzas.gob.bo/presupuesto/descargas/gasto/ultimo/gasto.parquet",
    )
    validate_go_live_env()
