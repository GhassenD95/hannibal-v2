"""Tests for the contract lifecycle: request → interpret → confirm → workspace."""

import uuid

import pytest
from fastapi.testclient import TestClient

from apps.api.app.main import app
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def headers_for(email=ADMIN_EMAIL, password=ADMIN_PASSWORD):
    resp = TestClient(app).post("/auth/login",
                                json={"email": email, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


ADMIN = headers_for()
DRAFTER = headers_for("drafter@hannibal.local", "drafter123")
OTHER = headers_for("reviewer@other.local", "reviewer123")


def test_guided_wizard_to_confirmed_contract(client):
    headers = ADMIN
    name = f"Wizard Contract {uuid.uuid4().hex[:6]}"
    resp = client.post("/contracts", headers=headers, json={
        "name": name,
        "contract_type": "service_agreement",
        "jurisdiction": "MA",
        "mode": "guided",
        "facts": {"amount": "20000", "currency": "MAD"},
    })
    assert resp.status_code == 200, resp.text
    request_id = resp.json()["id"]

    resp = client.post(f"/contracts/{request_id}/confirm-request", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["kind"] == "contract"
    assert data["status"] == "requested"
    assert data["section_count"] >= 5
    titles = [s["title"] for s in data["sections"]]
    assert "Parties" in titles
    assert "Governing Law" in titles

    sections = client.get(f"/contracts/{data['id']}/sections", headers=headers)
    assert sections.status_code == 200
    assert len(sections.json()) == data["section_count"]


def test_ai_interpret_fills_facts(client):
    headers = ADMIN
    resp = client.post("/contracts", headers=headers, json={
        "name": "AI contract",
        "contract_type": "nda",
        "jurisdiction": "MA",
        "mode": "ai",
    })
    request_id = resp.json()["id"]
    resp = client.post(f"/contracts/{request_id}/interpret", headers=headers, json={
        "description": "12-month service agreement between Acme and Globex for 50000 MAD",
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["contract_type"] == "service_agreement"
    assert data["facts"]["amount"].strip() == "50000"
    assert data["facts"]["duration"] == "12 months"


def test_list_and_patch_contract(client):
    headers = ADMIN
    contracts = client.get("/contracts", headers=headers,
                           params={"contract_type": "service_agreement"})
    assert contracts.status_code == 200
    target = contracts.json()[0]
    resp = client.patch(f"/contracts/{target['id']}", headers=headers,
                        json={"name": f"Renamed {target['id']}"})
    assert resp.status_code == 200
    assert resp.json()["name"].startswith("Renamed")


def test_section_patch_and_status(client):
    headers = ADMIN
    contracts = client.get("/contracts", headers=headers).json()
    contract_id = contracts[0]["id"]
    sections = client.get(f"/contracts/{contract_id}/sections",
                          headers=headers).json()
    sid = sections[0]["id"]
    resp = client.patch(f"/contracts/{contract_id}/sections/{sid}",
                        headers=headers,
                        json={"content": "Drafted text for review",
                              "status": "needs_review"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "needs_review"


def test_section_evidence_endpoint_returns_list(client):
    headers = ADMIN
    contracts = client.get("/contracts", headers=headers).json()
    contract_id = contracts[0]["id"]
    sections = client.get(f"/contracts/{contract_id}/sections",
                          headers=headers).json()
    sid = sections[0]["id"]
    resp = client.get(f"/contracts/{contract_id}/sections/{sid}/evidence",
                      headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json()["evidence"], list)


class TestOrgScoping:
    def test_cross_org_contract_403(self, client):
        contracts = client.get("/contracts", headers=ADMIN).json()
        if not contracts:
            pytest.skip("no contracts available")
        target = contracts[0]["id"]
        resp = client.get(f"/contracts/{target}", headers=OTHER)
        assert resp.status_code == 403
        resp = client.patch(f"/contracts/{target}", headers=OTHER,
                            json={"name": "hijack"})
        assert resp.status_code == 403

    def test_org_list_is_filtered(self, client):
        other_contracts = client.get("/contracts", headers=OTHER).json()
        admin_contracts = client.get("/contracts", headers=ADMIN).json()
        if admin_contracts:
            admin_ids = {c["id"] for c in admin_contracts}
            other_ids = {c["id"] for c in other_contracts}
            assert not (admin_ids & other_ids) or other_ids == admin_ids

    def test_cross_org_section_403(self, client):
        contracts = client.get("/contracts", headers=ADMIN).json()
        if not contracts:
            pytest.skip("no contracts available")
        contract_id = contracts[0]["id"]
        resp = client.get(f"/contracts/{contract_id}/sections", headers=OTHER)
        assert resp.status_code == 403

    def test_cross_org_request_403(self, client):
        resp = client.post("/contracts", headers=DRAFTER, json={
            "name": "org1 request", "contract_type": "nda", "jurisdiction": "MA",
        })
        request_id = resp.json()["id"]
        resp = client.post(f"/contracts/{request_id}/interpret", headers=OTHER,
                           json={"description": "some nda description for org2"})
        assert resp.status_code == 403