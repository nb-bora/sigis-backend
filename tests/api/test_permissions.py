"""
Tests de contrôle d'accès — vérifie que chaque route protégée retourne bien
401 sans authentification et 200 avec le header X-User-Id (mode dev/test).
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.main import create_app


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture(scope="module")
def uid():
    return str(uuid4())


# ---------------------------------------------------------------------------
# Routes publiques (pas d'auth requise)
# ---------------------------------------------------------------------------


def test_login_public(client: TestClient) -> None:
    """POST /auth/login ne nécessite pas d'authentification."""
    r = client.post("/v1/auth/login", json={"email": "x@x.com", "password": "wrong"})
    # 401 identifiants incorrects, pas 401 "auth requise"
    assert r.status_code == 401
    assert "Authentification requise" not in r.text


def test_request_password_reset_public(client: TestClient) -> None:
    """POST /auth/request-password-reset est public (anti-énumération)."""
    r = client.post("/v1/auth/request-password-reset", json={"email": "nobody@example.com"})
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Routes protégées — 401 sans auth
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method,path,json_body",
    [
        (
            "POST",
            "/v1/auth/register",
            {
                "email": "a@b.com",
                "full_name": "A B",
                "phone_number": "699000001",
                "password": "pass1234",
                "roles": [],
            },
        ),
        ("GET", "/v1/users", None),
        ("GET", f"/v1/users/{uuid4()}", None),
        ("PATCH", f"/v1/users/{uuid4()}", {"full_name": "X"}),
        ("PATCH", f"/v1/users/{uuid4()}/roles", {"roles": []}),
        (
            "POST",
            "/v1/establishments",
            {
                "name": "X",
                "center_lat": 4.0,
                "center_lon": 9.0,
                "radius_strict_m": 100.0,
                "radius_relaxed_m": 200.0,
            },
        ),
        ("GET", "/v1/establishments", None),
        ("GET", f"/v1/establishments/{uuid4()}", None),
        ("PATCH", f"/v1/establishments/{uuid4()}", {"name": "Y"}),
        (
            "POST",
            "/v1/missions",
            {
                "establishment_id": str(uuid4()),
                "inspector_id": str(uuid4()),
                "window_start": "2026-01-01T08:00:00Z",
                "window_end": "2026-01-01T10:00:00Z",
            },
        ),
        ("GET", "/v1/missions", None),
        ("GET", f"/v1/missions/{uuid4()}", None),
        ("PATCH", f"/v1/missions/{uuid4()}", {"status": "cancelled"}),
        ("GET", f"/v1/missions/{uuid4()}/site-visit", None),
        ("GET", f"/v1/missions/{uuid4()}/exception-requests", None),
        ("POST", f"/v1/missions/{uuid4()}/exception-requests", {"message": "test"}),
        (
            "POST",
            f"/v1/missions/{uuid4()}/check-in",
            {
                "latitude": 4.0,
                "longitude": 9.0,
                "client_request_id": "x",
                "host_validation_mode": "app_gps",
            },
        ),
        ("GET", f"/v1/site-visits/{uuid4()}", None),
        (
            "POST",
            f"/v1/site-visits/{uuid4()}/host-confirmation",
            {"mission_id": str(uuid4()), "client_request_id": "y"},
        ),
        (
            "POST",
            f"/v1/site-visits/{uuid4()}/check-out",
            {"mission_id": str(uuid4()), "client_request_id": "z"},
        ),
        ("GET", "/v1/exception-requests", None),
        ("GET", f"/v1/exception-requests/{uuid4()}", None),
        ("PATCH", f"/v1/exception-requests/{uuid4()}/status", {"status": "acknowledged"}),
    ],
)
def test_protected_route_returns_401_without_auth(
    client: TestClient,
    method: str,
    path: str,
    json_body: dict | None,
) -> None:
    """Toute route protégée doit renvoyer 401 si aucune authentification n'est fournie."""
    r = client.request(method, path, json=json_body)
    assert r.status_code == 401, f"{method} {path} → attendu 401, reçu {r.status_code}: {r.text}"


# ---------------------------------------------------------------------------
# Routes protégées — 200/4xx avec X-User-Id (bypass dev)
# ---------------------------------------------------------------------------


def test_establishments_with_x_user_id(client: TestClient, uid: str) -> None:
    """POST /establishments est accessible en mode dev via X-User-Id."""
    r = client.post(
        "/v1/establishments",
        json={
            "name": "Test perm",
            "center_lat": 4.05,
            "center_lon": 9.76,
            "radius_strict_m": 100.0,
            "radius_relaxed_m": 200.0,
        },
        headers={"X-User-Id": uid},
    )
    assert r.status_code == 200, r.text


def test_list_establishments_with_x_user_id(client: TestClient, uid: str) -> None:
    """GET /establishments est accessible en mode dev via X-User-Id."""
    r = client.get("/v1/establishments", headers={"X-User-Id": uid})
    assert r.status_code == 200, r.text


def test_list_users_with_x_user_id(client: TestClient, uid: str) -> None:
    """GET /users est accessible en mode dev via X-User-Id."""
    r = client.get("/v1/users", headers={"X-User-Id": uid})
    assert r.status_code == 200, r.text


def test_list_missions_with_x_user_id(client: TestClient, uid: str) -> None:
    """GET /missions est accessible en mode dev via X-User-Id."""
    r = client.get("/v1/missions", headers={"X-User-Id": uid})
    assert r.status_code == 200, r.text


def test_list_exception_requests_with_x_user_id(client: TestClient, uid: str) -> None:
    """GET /exception-requests est accessible en mode dev via X-User-Id."""
    r = client.get("/v1/exception-requests", headers={"X-User-Id": uid})
    assert r.status_code == 200, r.text


def test_get_user_with_x_user_id(client: TestClient, uid: str) -> None:
    """GET /users/{id} retourne 404 (non 401/403) en mode dev — permission bypassée."""
    r = client.get(f"/v1/users/{uuid4()}", headers={"X-User-Id": uid})
    assert r.status_code == 404, r.text


def test_patch_user_with_x_user_id(client: TestClient, uid: str) -> None:
    """PATCH /users/{id} retourne 404 (non 401/403) en mode dev — permission bypassée."""
    r = client.patch(f"/v1/users/{uuid4()}", json={"full_name": "Test"}, headers={"X-User-Id": uid})
    assert r.status_code == 404, r.text
