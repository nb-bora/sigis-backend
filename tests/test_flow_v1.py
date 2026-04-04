"""Flux minimal V1 : établissement → mission → check-in → hôte → check-out."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from api.main import create_app


def test_full_flow_mode_a() -> None:
    with TestClient(create_app()) as client:
        _run_flow(client)


def _run_flow(client: TestClient) -> None:
    insp = uuid4()
    host = uuid4()
    admin = uuid4()

    # Enregistre l'inspecteur (nécessaire depuis que CreateMission vérifie l'existence)
    insp_hex = insp.hex
    # Mobile valide PNN (69x…) — 7 chiffres pseudo-aléatoires pour unicité
    phone_national = f"69{str(int(insp_hex[:8], 16) % 10**7).zfill(7)}"
    r_reg = client.post(
        "/v1/auth/register",
        json={
            "email": f"insp_{insp_hex[:8]}@test.cm",
            "full_name": "Inspecteur Test",
            "phone_number": phone_national,
            "password": "pass1234",
            "roles": ["INSPECTOR"],
        },
        headers={"X-User-Id": str(admin)},
    )
    assert r_reg.status_code == 201, r_reg.text
    insp = r_reg.json()["user_id"]

    r0 = client.post(
        "/v1/establishments",
        json={
            "name": "Lycée test",
            "center_lat": 4.0511,
            "center_lon": 9.7679,
            "radius_strict_m": 500.0,
            "radius_relaxed_m": 800.0,
        },
        headers={"X-User-Id": str(admin)},
    )
    assert r0.status_code == 200, r0.text
    eid = r0.json()["establishment_id"]

    now = datetime.now(UTC)
    r1 = client.post(
        "/v1/missions",
        json={
            "establishment_id": eid,
            "inspector_id": str(insp),
            "window_start": (now - timedelta(hours=1)).isoformat(),
            "window_end": (now + timedelta(hours=2)).isoformat(),
        },
        headers={"X-User-Id": str(insp)},
    )
    assert r1.status_code == 200, r1.text
    mid = r1.json()["mission_id"]

    # Position proche du centre (Douala approx)
    r2 = client.post(
        f"/v1/missions/{mid}/check-in",
        json={
            "latitude": 4.0511,
            "longitude": 9.7679,
            "client_request_id": "ci-req-001",
            "host_validation_mode": "app_gps",
        },
        headers={"X-User-Id": str(insp)},
    )
    assert r2.status_code == 200, r2.text
    sv = r2.json()["site_visit_id"]

    r3 = client.post(
        f"/v1/site-visits/{sv}/host-confirmation",
        json={
            "mission_id": mid,
            "client_request_id": "host-req-001",
            "latitude": 4.0512,
            "longitude": 9.7680,
        },
        headers={"X-User-Id": str(host)},
    )
    assert r3.status_code == 200, r3.text

    r4 = client.post(
        f"/v1/site-visits/{sv}/check-out",
        json={"mission_id": mid, "client_request_id": "co-req-001"},
        headers={"X-User-Id": str(insp)},
    )
    assert r4.status_code == 200, r4.text
    assert r4.json()["presence_duration_seconds"] is not None
