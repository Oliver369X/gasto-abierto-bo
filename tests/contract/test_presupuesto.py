from pathlib import Path

from common.presupuesto_csv import build_header_map, parse_csv_bytes, row_to_budget_dict
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


def test_presupuesto_abierto_csv():
    adapter = PresupuestoAbiertoAdapter()
    path = FIXTURES / "presupuesto_abierto" / "sample_export.csv"
    items = adapter.discover(Cursor(payload={"fixture_path": str(path)}))
    records = adapter.parse(adapter.fetch(items[0]))
    assert len(records) >= 10
    assert records[0].record_type == "budget"
    assert records[0].data["department"]
    assert records[0].data["source_note"] == "presupuesto_abierto_csv"


def test_presupuesto_csv_column_mapping():
    raw = FIXTURES / "presupuesto_abierto" / "sample_export.csv"
    rows = parse_csv_bytes(raw.read_bytes())
    assert len(rows) >= 10
    assert rows[0]["entity_name"] == "Ministerio de Educación"
    assert rows[0]["year"] == 2025


def test_presupuesto_abierto_fixture_fallback_discover():
    adapter = PresupuestoAbiertoAdapter()
    items = adapter.discover(Cursor(payload={}))
    assert items, "expected bundled fixture fallback when no env URLs"
    assert all(i.uri.startswith("file://") for i in items)
    records = adapter.parse(adapter.fetch(items[0]))
    assert records
    assert records[0].record_type == "budget"


def test_presupuesto_csv_header_aliases():
    header = build_header_map(["gestion", "institucion", "ppto_vigente", "pagado"])
    mapped = row_to_budget_dict(
        {
            "gestion": "2024",
            "institucion": "Ministerio X",
            "ppto_vigente": "1000",
            "pagado": "500",
        },
        header,
    )
    assert mapped is not None
    assert mapped["entity_name"] == "Ministerio X"
    assert mapped["year"] == 2024
