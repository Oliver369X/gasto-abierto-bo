from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_openapi_has_contracts():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    assert "/v1/contracts" in paths


def test_openapi_has_fire_ledger():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    assert "/v1/fire/ledger" in paths
    assert "/v1/fire/expenditures" in paths
    assert "/v1/fire/operations" in paths
    assert "/v1/fire/metrics" in paths
    assert "/v1/fire/seasons" in paths
