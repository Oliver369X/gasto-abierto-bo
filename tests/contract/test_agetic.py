from pathlib import Path

from worker.adapters.agetic import AgeticAdapter
from worker.adapters.base import Cursor

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_agetic_csv_parse():
    adapter = AgeticAdapter()
    path = FIXTURES / "agetic" / "sample_contracts.csv"
    items = adapter.discover(Cursor(payload={"fixture_path": str(path)}))
    assert len(items) == 1
    raw = adapter.fetch(items[0])
    records = adapter.parse(raw)
    assert len(records) == 3
    assert records[0].record_type == "contract"
    assert records[0].data["cuce"] == "OCDS-DEMO-001"
    assert records[0].data["source_id"] == "agetic"
