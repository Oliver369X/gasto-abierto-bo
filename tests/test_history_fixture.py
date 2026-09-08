from pathlib import Path

from worker.adapters.agetic import AgeticAdapter
from worker.adapters.base import Cursor
from worker.adapters.presupuesto_abierto import PresupuestoAbiertoAdapter
import json

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _budget_entities() -> set[str]:
    path = FIXTURES / "presupuesto_abierto" / "history_2019_2025.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {row["entidad"] for row in data["series"]}


def _contract_entities() -> set[str]:
    adapter = AgeticAdapter()
    path = FIXTURES / "agetic" / "contracts_history_2019_2025.csv"
    items = adapter.discover(Cursor(payload={"fixture_path": str(path)}))
    records = adapter.parse(adapter.fetch(items[0]))
    return {r.data.get("entity_name") or "" for r in records}


def test_history_contracts_span_years():
    adapter = AgeticAdapter()
    path = FIXTURES / "agetic" / "contracts_history_2019_2025.csv"
    items = adapter.discover(Cursor(payload={"fixture_path": str(path)}))
    records = adapter.parse(adapter.fetch(items[0]))
    assert len(records) >= 25
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
    assert len(data["series"]) >= 60


def test_history_presupuesto_contract_entity_alignment():
    budget = _budget_entities()
    contracts = _contract_entities()
    overlap = budget & contracts
    assert len(overlap) >= 8
    assert "Ministerio de Educación" in overlap
    assert "GAM Santa Cruz de la Sierra" in overlap
    assert "GAD La Paz" in overlap
    assert "Gobernación de Cochabamba" in overlap
    budget_only = budget - contracts
    contract_only = contracts - budget
    assert len(budget_only) <= 1
    assert len(contract_only) <= 1


def test_history_each_core_entity_has_multi_year_budget():
    path = FIXTURES / "presupuesto_abierto" / "history_2019_2025.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    by_entity: dict[str, set[int]] = {}
    for row in data["series"]:
        by_entity.setdefault(row["entidad"], set()).add(int(row["gestion"]))
    for ent in (
        "Ministerio de Educación",
        "GAM La Paz",
        "GAD Santa Cruz",
        "Ministerio de Salud",
    ):
        assert len(by_entity[ent]) >= 5
