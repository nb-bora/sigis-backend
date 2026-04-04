"""
Tests RBAC basés sur de vrais JWT — vérifie que les contrôles d'accès
fonctionnent avec des tokens signés contenant des rôles spécifiques.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from domain.identity.role import Role

_SECRET = "test-secret-key-for-sigis-rbac-tests-only-xxxxxxxxxxxxx"
_ALG = "HS256"


def _make_token(user_id: str, roles: list[str], secret: str = _SECRET) -> str:
    payload = {
        "sub": user_id,
        "email": f"{user_id[:8]}@test.cm",
        "roles": roles,
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    return jwt.encode(payload, secret, algorithm=_ALG)


@pytest.fixture(scope="module")
def client():
    import os

    os.environ["SIGIS_SECRET_KEY"] = _SECRET
    os.environ["SIGIS_JWT_ALGORITHM"] = _ALG
    with TestClient(create_app()) as c:
        yield c


# ── Helpers ─────────────────────────────────────────────────────────────────


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Expired / malformed token ────────────────────────────────────────────────


def test_expired_token_returns_401(client: TestClient) -> None:
    expired_payload = {
        "sub": str(uuid4()),
        "roles": [],
        "exp": datetime.now(UTC) - timedelta(seconds=1),
    }
    token = jwt.encode(expired_payload, _SECRET, algorithm=_ALG)
    r = client.get("/v1/users", headers=_auth(token))
    assert r.status_code == 401
    assert "expiré" in r.json()["detail"]


def test_invalid_signature_returns_401(client: TestClient) -> None:
    token = _make_token(str(uuid4()), [], secret="wrong-secret-key-not-the-same-as-test-suite-xxx")
    r = client.get("/v1/users", headers=_auth(token))
    assert r.status_code == 401


# ── Permission checks ────────────────────────────────────────────────────────


def test_no_admin_role_cannot_list_users(client: TestClient) -> None:
    """Un INSPECTOR ne peut pas lister tous les utilisateurs (USER_LIST manquant)."""
    token = _make_token(str(uuid4()), [Role.INSPECTOR.value])
    r = client.get("/v1/users", headers=_auth(token))
    assert r.status_code == 403


def test_super_admin_can_list_users(client: TestClient) -> None:
    """Un SUPER_ADMIN a la permission USER_LIST."""
    token = _make_token(str(uuid4()), [Role.SUPER_ADMIN.value])
    r = client.get("/v1/users", headers=_auth(token))
    assert r.status_code == 200


def test_inspector_can_read_own_profile(client: TestClient) -> None:
    """Un INSPECTOR peut lire son propre profil (owner check)."""
    uid = str(uuid4())
    token = _make_token(uid, [Role.INSPECTOR.value])
    r = client.get(f"/v1/users/{uid}", headers=_auth(token))
    # 404 car l'utilisateur n'est pas en base — pas 401/403
    assert r.status_code == 404


def test_inspector_cannot_read_other_profile(client: TestClient) -> None:
    """Un INSPECTOR ne peut pas lire le profil d'un autre utilisateur."""
    token = _make_token(str(uuid4()), [Role.INSPECTOR.value])
    r = client.get(f"/v1/users/{uuid4()}", headers=_auth(token))
    assert r.status_code == 403


def test_super_admin_can_read_any_profile(client: TestClient) -> None:
    """Un SUPER_ADMIN peut lire n'importe quel profil."""
    token = _make_token(str(uuid4()), [Role.SUPER_ADMIN.value])
    r = client.get(f"/v1/users/{uuid4()}", headers=_auth(token))
    assert r.status_code == 404  # 404 = utilisateur introuvable, pas 403


def test_inspector_cannot_set_is_active(client: TestClient) -> None:
    """Un INSPECTOR ne peut pas désactiver un compte (champ admin)."""
    uid = str(uuid4())
    token = _make_token(uid, [Role.INSPECTOR.value])
    r = client.patch(f"/v1/users/{uid}", json={"is_active": False}, headers=_auth(token))
    assert r.status_code == 403


def test_inspector_cannot_set_roles(client: TestClient) -> None:
    """Un INSPECTOR ne peut pas modifier les rôles (champ admin)."""
    uid = str(uuid4())
    token = _make_token(uid, [Role.INSPECTOR.value])
    r = client.patch(f"/v1/users/{uid}", json={"roles": ["SUPER_ADMIN"]}, headers=_auth(token))
    assert r.status_code == 403


def test_super_admin_can_set_is_active(client: TestClient) -> None:
    """Un SUPER_ADMIN peut modifier is_active."""
    token = _make_token(str(uuid4()), [Role.SUPER_ADMIN.value])
    r = client.patch(f"/v1/users/{uuid4()}", json={"is_active": False}, headers=_auth(token))
    assert r.status_code == 404  # 404 = user introuvable, pas 403


def test_inspector_cannot_register_user(client: TestClient) -> None:
    """Un INSPECTOR ne peut pas enregistrer un utilisateur (AUTH_REGISTER_USER manquant)."""
    token = _make_token(str(uuid4()), [Role.INSPECTOR.value])
    r = client.post(
        "/v1/auth/register",
        json={
            "email": "new@test.cm",
            "full_name": "New User",
            "phone_number": "699000099",
            "password": "pass1234",
            "roles": [],
        },
        headers=_auth(token),
    )
    assert r.status_code == 403


def test_super_admin_can_register_user(client: TestClient) -> None:
    """Un SUPER_ADMIN peut enregistrer un utilisateur."""
    token = _make_token(str(uuid4()), [Role.SUPER_ADMIN.value])
    r = client.post(
        "/v1/auth/register",
        json={
            "email": f"rbac_{uuid4().hex[:8]}@test.cm",
            "full_name": "Test RBAC",
            "phone_number": "699000077",
            "password": "pass1234",
            "roles": [],
        },
        headers=_auth(token),
    )
    assert r.status_code == 201
