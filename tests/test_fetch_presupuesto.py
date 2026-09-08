"""Tests for Presupuesto Abierto URL discovery and offline fallback."""
from __future__ import annotations

from pathlib import Path

from common.fetch_presupuesto_abierto import (
    DOCUMENTED_DOWNLOADS,
    copy_fixture_fallback,
    discover_download_urls,
    list_download_urls,
    list_offline_corpus_paths,
    load_offline_manifest,
    offline_corpus_ready,
)


def test_documented_parquet_urls_are_direct_files():
    for name, url in DOCUMENTED_DOWNLOADS:
        assert url.startswith("https://")
        assert url.endswith((".parquet", ".csv", ".zip"))
        assert "descargas" in url
        assert name


def test_discover_includes_documented_without_network(monkeypatch):
    monkeypatch.setattr(
        "common.fetch_presupuesto_abierto._client",
        lambda: (_ for _ in ()).throw(RuntimeError("no network")),
    )
    urls = discover_download_urls(fetch_page=False)
    assert len(urls) >= 2
    assert any(u.endswith("gasto.parquet") for u in urls)


def test_list_download_urls_respects_env(monkeypatch):
    monkeypatch.setenv("PRESUPUESTO_ABIERTO_DOWNLOAD_URLS", "https://example.test/a.csv")
    assert list_download_urls(discover=False) == ["https://example.test/a.csv"]


def test_copy_fixture_fallback(tmp_path: Path):
    wrote = copy_fixture_fallback(tmp_path)
    assert wrote
    names = {p.name for p in wrote}
    assert "entidades.json" in names or "sample_export.csv" in names
    assert "regional_entities.csv" in names


def test_offline_corpus_manifest_paths_exist():
    manifest = load_offline_manifest()
    assert manifest.get("version")
    paths = list_offline_corpus_paths()
    assert offline_corpus_ready()
    assert len(paths) >= 4
    assert any(p.name == "regional_entities.csv" for p in paths)
