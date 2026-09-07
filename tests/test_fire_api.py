"""API tests for fire ledger endpoints against running Postgres (or empty tables)."""
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_fire_ledger_endpoint():
    r = client.get("/v1/fire/ledger?year=2024")
    assert r.status_code == 200
    body = r.json()
    assert body["year"] == 2024
    assert "amount_direct_verifiable" in body
    assert "disclaimer" in body
    assert "by_attribution" in body
    assert "verificable" in body["disclaimer"].lower()


def test_fire_expenditures_list():
    r = client.get("/v1/fire/expenditures?year=2024&limit=5")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_fire_operations_list():
    r = client.get("/v1/fire/operations?year=2024")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_fire_metrics():
    r = client.get("/v1/fire/metrics?year=2024")
    assert r.status_code == 200
    body = r.json()
    assert body["year"] == 2024
    assert "notes" in body


def test_fire_seasons():
    r = client.get("/v1/fire/seasons")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_fire_capabilities_summary():
    r = client.get("/v1/fire/capabilities/summary?year=2024")
    assert r.status_code == 200
    body = r.json()
    assert body["year"] == 2024
    assert {"preventive_assets", "reactive_rentals", "by_type", "items"} <= body.keys()


def test_fire_coverage_geojson_has_three_departments():
    r = client.get("/v1/fire/coverage.geojson?year=2024")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == 3
    assert {feature["properties"]["slug"] for feature in body["features"]} == {
        "santa-cruz", "beni", "pando"
    }
    for feature in body["features"]:
        assert feature["properties"]["level"] in {"Alta", "Media", "Baja", "Sin datos"}
        assert "amount_direct_verifiable" in feature["properties"]
