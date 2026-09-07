from pathlib import Path

from worker.adapters.base import Cursor
from worker.adapters.sicoes import SicoesAdapter

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_sicoes_html_parse():
    adapter = SicoesAdapter()
    path = FIXTURES / "sicoes" / "procesos_sample.html"
    items = adapter.discover(Cursor(payload={"fixture_path": str(path)}))
    raw = adapter.fetch(items[0])
    records = adapter.parse(raw)
    assert len(records) >= 2
    assert records[0].data["cuce"] == "26-1234-00-000111-1-1"
    assert "Santa Cruz" in (records[0].data["entity_name"] or "")
    assert records[0].data["amount"]
    assert records[0].data["supplier_name"]
