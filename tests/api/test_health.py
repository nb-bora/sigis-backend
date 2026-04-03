from fastapi.testclient import TestClient

from api.main import create_app


def test_health() -> None:
    client = TestClient(create_app())
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
