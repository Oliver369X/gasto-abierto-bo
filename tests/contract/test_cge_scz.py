from pathlib import Path

from worker.adapters.base import Cursor
from worker.adapters.cge import CgeAdapter
from worker.adapters.scz import GadSczAdapter, GamSczAdapter

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_cge_parse():
    adapter = CgeAdapter()
    path = FIXTURES / "cge" / "informes_sample.html"
    records = adapter.parse(adapter.fetch(adapter.discover(Cursor(payload={"fixture_path": str(path)}))[0]))
    assert len(records) >= 3
    assert records[0].record_type == "audit"


def test_gad_scz_parse():
    adapter = GadSczAdapter()
    path = FIXTURES / "gad_scz" / "portal_sample.html"
    records = adapter.parse(adapter.fetch(adapter.discover(Cursor(payload={"fixture_path": str(path)}))[0]))
    types = {r.record_type for r in records}
    assert "document" in types
    assert "budget" in types


def test_gam_scz_text_parse():
    adapter = GamSczAdapter()
    path = FIXTURES / "gam_scz" / "rendicion_text.txt"
    records = adapter.parse(adapter.fetch(adapter.discover(Cursor(payload={"fixture_path": str(path)}))[0]))
    assert len(records) == 1
    assert records[0].data["initial_amount"]
    assert records[0].data["executed_amount"]
