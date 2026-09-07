from pathlib import Path

from worker.adapters.agetic import AgeticAdapter
from worker.adapters.base import Cursor
from worker.adapters.presupuesto_abierto import PresupuestoAbiertoAdapter
import json

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_history_contracts_span_years():
    adapter = AgeticAdapter()
    path = FIXTURES / "agetic" / "contracts_history_2019_2025.csv"
    items = adapter.discover(Cursor(payload={"fixture_path": str(path)}))
    records = adapter.parse(adapter.fetch(items[0]))
    assert len(records) >= 20
    years = set()
    for r in records:
        d = r.data.get("contract_date") or ""
        if len(d) >= 4:
            years.add(d[:4])
    assert "2019" in years and "2025" in years


def test_history_budgets_span_years():
    path = FIXTURES / "presupuesto_abierto" / "history_2019_2025.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    adapter = PresupuestoAbiertoAdapter()
    years = set()
    for row in data["series"]:
        payload = {"entidades": [row | {"gestion": row["gestion"]}]}
        # normalize keys for parser
        payload["entidades"][0] = {
            "entidad": row["entidad"],
            "nivel": row["nivel"],
            "gestion": row["gestion"],
            "presupuesto_inicial": row["presupuesto_inicial"],
            "presupuesto_vigente": row["presupuesto_vigente"],
            "ejecucion": row["ejecucion"],
        }
        recs = adapter.parse(json.dumps(payload).encode("utf-8"))
        years.add(int(recs[0].data["year"]))
    assert min(years) <= 2019 and max(years) >= 2025
