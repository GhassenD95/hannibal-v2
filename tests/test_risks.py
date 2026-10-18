"""Risk analysis tests."""

import uuid

import pytest
from fastapi.testclient import TestClient

from apps.api.app.main import app
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def admin_headers():
    resp = TestClient(app).post("/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD,
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def make_generated_contract(client):
    headers = admin_headers()
    name = f"Risk {uuid.uuid4().hex[:6]}"
    resp = client.post("/contracts", headers=headers, json={
        "name": name, "contract_type": "service_agreement",
        "jurisdiction": "MA",
    })
    request_id = resp.json()["id"]
    resp = client.post(f"/contracts/{request_id}/confirm-request", headers=headers)
    contract_id = resp.json()["id"]
    client.post(f"/contracts/{contract_id}/generate", headers=headers)
    client.post(f"/contracts/{contract_id}/validate", headers=headers)
    return headers, contract_id


class TestRiskAnalysis:
    def test_risk_run_persists_findings_per_section(self, client):
        headers, contract_id = make_generated_contract(client)
        resp = client.post(f"/contracts/{contract_id}/risk", headers=headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["risk_count"] > 0
        assert "requires_human_review" in data

        risks = client.get(f"/contracts/{contract_id}/risks", headers=headers)
        assert risks.status_code == 200
        items = risks.json()
        assert len(items) == data["risk_count"]
        assert any(r["section_id"] is not None for r in items)
        assert all(r["status"] == "open" for r in items)

    def test_risks_cross_org_403(self, client):
        headers, contract_id = make_generated_contract(client)
        other = TestClient(app).post("/auth/login", json={
            "email": "reviewer@other.local", "password": "reviewer123",
        }).json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other}"}
        resp = client.get(f"/contracts/{contract_id}/risks", headers=other_headers)
        assert resp.status_code == 403