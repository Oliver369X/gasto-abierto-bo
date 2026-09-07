"""Contract tests for MINDEF / ABT fire adapters (offline fixtures)."""
from pathlib import Path

from worker.adapters.abt import AbtAdapter
from worker.adapters.base import Cursor
from worker.adapters.mindef import MindefAdapter

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"


def test_mindef_rpc_fixture_parses_operations():
    adapter = MindefAdapter()
    path = FIXTURES / "mindef" / "rpc_2024.json"
    items = adapter.discover(Cursor(payload={"fixture_path": str(path)}))
    raw = adapter.fetch(items[0])
    records = adapter.parse(raw)
    ops = [r for r in records if r.record_type == "fire_operational"]
    assert len(ops) >= 8
    keys = {r.data["metric_key"] for r in ops}
    assert "bomberos_forestales" in keys
    assert "procesos_aeronaves" in keys
    assert "incendios_mitigados" in keys


def test_abt_fixture_parses_budgets():
    adapter = AbtAdapter()
    path = FIXTURES / "abt" / "ejecucion_2024.json"
    items = adapter.discover(Cursor(payload={"fixture_path": str(path)}))
    raw = adapter.fetch(items[0])
    records = adapter.parse(raw)
    budgets = [r for r in records if r.record_type == "budget"]
    assert len(budgets) >= 2
    assert any("incendio" in (b.data.get("program_project") or "").lower() for b in budgets)
