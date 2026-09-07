"""Tests for expanded fire adapters."""
from pathlib import Path

from worker.adapters.base import Cursor
from worker.adapters.firms import FirmsAdapter
from worker.adapters.gaceta_scz import GacetaSczAdapter
from worker.adapters.sernap import SernapAdapter
from worker.alerts_fire import run_fire_alert_rules

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"


def test_gaceta_parses_declarations():
    a = GacetaSczAdapter()
    path = FIXTURES / "gaceta_scz" / "decretos_incendio.json"
    raw = a.fetch(a.discover(Cursor(payload={"fixture_path": str(path)}))[0])
    recs = a.parse(raw)
    assert any(r.record_type == "emergency_declaration" for r in recs)
    types = {r.data["event_type"] for r in recs}
    assert "incendio_forestal" in types
    assert "inundacion" in types  # negative control present


def test_firms_parses_detections_and_aggregates():
    a = FirmsAdapter()
    path = FIXTURES / "firms" / "bolivia_2024_sample.json"
    raw = a.fetch(a.discover(Cursor(payload={"fixture_path": str(path)}))[0])
    recs = a.parse(raw)
    dets = [r for r in recs if r.record_type == "active_fire_detection"]
    ops = [r for r in recs if r.record_type == "fire_operational"]
    assert len(dets) >= 5
    assert len(ops) >= 1


def test_sernap_fixture():
    a = SernapAdapter()
    path = FIXTURES / "sernap" / "incendios_ap.json"
    raw = a.fetch(a.discover(Cursor(payload={"fixture_path": str(path)}))[0])
    recs = a.parse(raw)
    assert any(r.record_type == "fire_operational" for r in recs)
    assert any(r.record_type == "fire_expenditure_candidate" for r in recs)
