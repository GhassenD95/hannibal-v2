"""Tests for the admin module: pack import/activation, source governance, RBAC."""

import pytest
from fastapi.testclient import TestClient

from apps.api.app.main import app
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD

SERVICE_PACK = "ma-service-agreement.json"


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def admin_headers():
    resp = client_logger.post("/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD,
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


client_logger = TestClient(app)


class TestPackImport:
    def test_import_service_pack_creates_entities(self, client):
        headers = admin_headers()
        resp = client.post("/admin/packs/import",
                           json={"path": SERVICE_PACK}, headers=headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["name"] == "Morocco Service Agreement Pack"
        assert data["status"] in {"draft", "active"}
        assert "service_agreement" in {
            ct["name"] for ct in data["contractTypes"]
        }
        assert data["clauseCount"] >= 4
        assert data["sourceCount"] >= 1

    def test_pack_validate_and_activate(self, client):
        headers = admin_headers()
        packs = client.get("/admin/packs", headers=headers).json()
        pack = next(p for p in packs if p["name"] == "Morocco Service Agreement Pack")
        resp = client.post(f"/admin/packs/{pack['id']}/validate", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["valid"] is True
        resp = client.post(f"/admin/packs/{pack['id']}/activate", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    def test_sources_approved_after_demo_import(self, client):
        headers = admin_headers()
        sources = client.get("/admin/sources", headers=headers).json()
        morocco_sources = [s for s in sources
                           if s.get("effective_date")]
        approved = [s for s in sources if s["status"] == "approved"]
        assert approved, "demo import should auto-approve sources"

    def test_retrieval_excludes_non_approved_source(self, client):
        headers = admin_headers()
        sources = client.get("/admin/sources", headers=headers).json()
        doc = next(s for s in sources if "D.O.C." in s["title"])
        client.post(f"/admin/sources/{doc['id']}/archive", headers=headers)
        resp = client.post("/admin/sources/test-retrieval",
                           json={"query": "Obligations must be performed in good faith"},
                           headers=headers)
        assert resp.status_code == 200
        for hit in resp.json()["hits"]:
            assert "D.O.C." not in (hit.get("title") or hit.get("source_title", "")), \
                "archived source must not be retrievable"
        # restore for later suites
        client.post(f"/admin/sources/{doc['id']}/approve", headers=headers)

    def test_pack_import_rejects_path_traversal(self, client):
        headers = admin_headers()
        resp = client.post("/admin/packs/import",
                           json={"path": "../../etc/passwd"}, headers=headers)
        assert resp.status_code == 400

    def test_non_admin_cannot_access_admin(self, client):
        token = client.post("/auth/login", json={
            "email": "drafter@hannibal.local", "password": "drafter123",
        }).json()["access_token"]
        resp = client.get("/admin/packs", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403


class TestClauseAdmin:
    def test_clause_crud(self, client):
        headers = admin_headers()
        resp = client.post("/admin/clauses", headers=headers, json={
            "title": "Test only clause",
            "content": "Test content",
            "contract_type": "service_agreement",
            "status": "draft",
        })
        assert resp.status_code == 200
        clause_id = resp.json()["id"]
        resp = client.post(f"/admin/clauses/{clause_id}/archive", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "archived"
        clauses = client.get("/admin/clauses?status=archived", headers=headers).json()
        assert any(c["id"] == clause_id for c in clauses)