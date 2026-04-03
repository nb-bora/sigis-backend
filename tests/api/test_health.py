from fastapi.testclient import TestClient

from api.main import create_app


def test_health() -> None:
    with TestClient(create_app()) as client:
        r = client.get("/v1/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
