from pathlib import Path

from worker.adapters.base import Cursor
from worker.adapters.presupuesto_abierto import PresupuestoAbiertoAdapter

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_presupuesto_abierto_json():
    adapter = PresupuestoAbiertoAdapter()
    path = FIXTURES / "presupuesto_abierto" / "entidades.json"
    items = adapter.discover(Cursor(payload={"fixture_path": str(path)}))
    records = adapter.parse(adapter.fetch(items[0]))
    assert len(records) >= 10
    assert records[0].record_type == "budget"
    assert records[0].data["entity_name"]
