"""Tests for authentication and RBAC."""

import pytest
from fastapi.testclient import TestClient

from apps.api.app.main import app
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def login(client, email=ADMIN_EMAIL, password=ADMIN_PASSWORD):
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


class TestAuth:
    def test_login_success(self, client):
        data = login(client)
        assert data["access_token"]
        assert data["email"] == ADMIN_EMAIL
        assert "admin" in data["roles"]

    def test_login_wrong_password(self, client):
        resp = client.post("/auth/login", json={
            "email": ADMIN_EMAIL, "password": "wrong",
        })
        assert resp.status_code == 401

    def test_me(self, client):
        token = login(client)["access_token"]
        resp = client.get("/auth/me", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json()["email"] == ADMIN_EMAIL

    def test_me_invalid_token(self, client):
        resp = client.get("/auth/me", headers=auth_headers("not.a.token"))
        assert resp.status_code == 401

    def test_non_admin_cannot_create_user(self, client):
        token = login(client, "drafter@hannibal.local", "drafter123")["access_token"]
        resp = client.post("/auth/users", headers=auth_headers(token), json={
            "email": "new@hannibal.local", "password": "pw123456",
        })
        assert resp.status_code == 403

    def test_admin_can_create_user(self, client):
        import uuid

        email = f"new-{uuid.uuid4().hex[:8]}@hannibal.local"
        token = login(client)["access_token"]
        resp = client.post("/auth/users", headers=auth_headers(token), json={
            "email": email, "password": "pw123456",
        })
        assert resp.status_code == 200
        assert resp.json()["email"] == email