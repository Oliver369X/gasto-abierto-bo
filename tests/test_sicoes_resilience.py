"""SICOES offline resilience — CI must stay green without live network."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from worker.adapters.base import Cursor
from worker.adapters.sicoes import SicoesAdapter, load_offline_fixture
from worker.adapters.sicoes_fetch import FetchError
from worker.adapters.sicoes_html import SicoesStructureChanged, inspect_list_html

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_offline_fixture_always_parseable():
    raw = load_offline_fixture()
    inspection = inspect_list_html(raw)
    assert inspection.parseable
    adapter = SicoesAdapter()
    records = adapter.parse(raw)
    assert len(records) >= 2
    assert records[0].data["cuce"]


def test_fetch_timeout_falls_back_to_fixture():
    adapter = SicoesAdapter()
    item = adapter.discover(Cursor(payload={"live": True}))[0]
    with patch(
        "worker.adapters.sicoes_fetch.fetch_page",
        side_effect=FetchError(item.uri, TimeoutError("timeout"), 2),
    ):
        raw = adapter.fetch(item)
    records = adapter.parse(raw)
    assert len(records) >= 2


def test_html_structure_change_falls_back_to_fixture():
    adapter = SicoesAdapter()
    broken = b"<html><body><h1>Portal en mantenimiento</h1></body></html>"
    inspection = inspect_list_html(broken)
    assert not inspection.parseable
    with patch.dict("os.environ", {"SICOES_OFFLINE_FALLBACK": "1"}):
        records = adapter.parse(broken)
    assert len(records) >= 2


def test_structure_change_raises_when_fallback_disabled():
    adapter = SicoesAdapter()
    broken = b"<html><body><p>Sin tablas</p></body></html>"
    with patch.dict("os.environ", {"SICOES_OFFLINE_FALLBACK": "0"}):
        try:
            adapter.parse(broken)
            raised = False
        except SicoesStructureChanged:
            raised = True
    assert raised


def test_fetch_empty_body_falls_back_to_fixture():
    adapter = SicoesAdapter()
    item = adapter.discover(Cursor(payload={"live": True}))[0]
    with patch(
        "worker.adapters.sicoes_fetch.fetch_page",
        side_effect=FetchError(item.uri, ValueError("response too small (12 bytes)"), 2),
    ):
        raw = adapter.fetch(item)
    records = adapter.parse(raw)
    assert len(records) >= 2


def test_fetch_cuce_detail_soft_fails_without_crash():
    adapter = SicoesAdapter()
    with patch.dict("os.environ", {"PROXY_URL": "http://proxy.test:7890"}):
        with patch(
            "worker.adapters.sicoes_fetch.fetch_page",
            side_effect=FetchError("http://test", TimeoutError("timeout"), 2),
        ):
            assert adapter.fetch_cuce_detail("TEST-CUCE-001") is None
    """Mirror CI ingest path — no network, fixture only."""
    import os

    from sqlalchemy.orm import sessionmaker

    from schema.db import make_engine
    from worker.pipeline import run_ingest

    url = os.getenv("DATABASE_URL")
    if not url:
        return  # skip when DB unavailable in lightweight CI shard
    try:
        engine = make_engine(url)
        engine.connect().close()
    except Exception:
        return

    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    fixture = str(FIXTURES / "sicoes" / "procesos_sample.html")
    try:
        result = run_ingest(
            session,
            "sicoes",
            fixture_path=fixture,
            live=False,
            skip_alerts=True,
            skip_storage=True,
        )
        session.commit()
        assert result["status"] in ("ok", "partial")
        assert result["records"] >= 1
    finally:
        session.rollback()
        session.close()
