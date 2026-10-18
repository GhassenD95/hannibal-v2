"""Versioning, approval, negotiation, and real-format export tests."""

import json
import uuid

import pytest
from fastapi.testclient import TestClient

from apps.api.app.main import app
from apps.api.app.modules.core.db import engine
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
    name = f"A6 {uuid.uuid4().hex[:6]}"
    resp = client.post("/contracts", headers=headers, json={
        "name": name, "contract_type": "service_agreement",
        "jurisdiction": "MA",
    })
    request_id = resp.json()["id"]
    resp = client.post(f"/contracts/{request_id}/confirm-request", headers=headers)
    contract_id = resp.json()["id"]
    client.post(f"/contracts/{contract_id}/generate", headers=headers)
    return headers, contract_id


class TestVersionSnapshots:
    def test_patch_creates_immutable_version_snapshot(self, client):
        from sqlmodel import Session, select
        from apps.api.app.modules.core.models import ContractVersion
        headers, contract_id = make_generated_contract(client)

        sections = client.get(f"/contracts/{contract_id}/sections",
                              headers=headers).json()
        target = next(s for s in sections if s["title"] != "")

        client.patch(f"/contracts/{contract_id}/sections/{target['id']}",
                     headers=headers, json={"content": "First edited wording."})
        client.patch(f"/contracts/{contract_id}/sections/{target['id']}",
                     headers=headers, json={"content": "Second edited wording."})

        versions = client.get(f"/contracts/{contract_id}/versions",
                              headers=headers).json()
        assert len(versions) >= 2
        active = [v for v in versions if v["is_active"]]
        assert active and active[0]["version_number"] == versions[-1]["version_number"]

        def fetch_rows():
            with Session(engine) as session:
                return list(session.exec(select(ContractVersion).where(
                    ContractVersion.contract_id == contract_id).order_by(
                    ContractVersion.version_number)).all())

        rows = fetch_rows()
        assert len(rows) >= 2
        # The snapshot taken before the second edit captured the first edit
        assert "First edited wording." in json.loads(rows[-1].content).get(
            target["title"], {}).get("content", "")
        # v1 (pre-edit state) and v2 (first edit) are distinct snapshots
        assert json.loads(rows[-1].content) != json.loads(rows[-2].content)

        # Immutability: a third edit must not rewrite the earlier snapshot
        before = rows[-1].content
        client.patch(f"/contracts/{contract_id}/sections/{target['id']}",
                     headers=headers, json={"content": "Third edited wording."})
        rows_after = fetch_rows()
        after_before_last = rows_after[-2].content
        assert after_before_last == before


class TestApproval:
    def test_approve_blocked_with_open_blockers_then_ok(self, client):
        headers, contract_id = make_generated_contract(client)

        client.post(f"/contracts/{contract_id}/validate", headers=headers)
        resp = client.post(f"/contracts/{contract_id}/approve", headers=headers,
                           json={"notes": "review"})
        assert resp.status_code == 400, resp.text
        assert "blocker" in resp.text.lower()

        sections = client.get(f"/contracts/{contract_id}/sections",
                              headers=headers).json()
        for section in sections:
            client.patch(f"/contracts/{contract_id}/sections/{section['id']}",
                         headers=headers,
                         json={"content": "Counterparty pays 5,000.00 USD "
                                          "in full within 30 days."})

        client.post(f"/contracts/{contract_id}/validate", headers=headers)
        resp = client.post(f"/contracts/{contract_id}/approve", headers=headers,
                           json={"notes": "approved"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["approval_type"] == "human"
        approvals = client.get(f"/contracts/{contract_id}/approvals",
                               headers=headers).json()
        assert len(approvals) >= 1

    def test_approve_cross_org_forbidden(self, client):
        headers, contract_id = make_generated_contract(client)
        other_resp = TestClient(app).post("/auth/login", json={
            "email": "reviewer@other.local", "password": "reviewer123",
        })
        other_headers = {
            "Authorization": f"Bearer {other_resp.json()['access_token']}"}
        resp = client.post(f"/contracts/{contract_id}/approve", headers=other_headers)
        assert resp.status_code == 403


class TestNegotiation:
    def test_negotiate_analyze_propose_decide(self, client):
        headers, contract_id = make_generated_contract(client)
        sections = client.get(f"/contracts/{contract_id}/sections",
                              headers=headers).json()
        section = next(s for s in sections if s["content"])

        create = client.post(f"/contracts/{contract_id}/negotiations",
                             headers=headers, json={
                                 "section_id": section["id"],
                                 "counterparty_clause": "Pay in 90 days.",
                             })
        assert create.status_code == 200, create.text
        item_id = create.json()["id"]

        analyzed = client.post(
            f"/contracts/{contract_id}/negotiations/{item_id}/analyze",
            headers=headers)
        assert analyzed.status_code == 200
        assert analyzed.json()["hannibal_analysis"]

        proposed = client.post(
            f"/contracts/{contract_id}/negotiations/{item_id}/propose",
            headers=headers)
        assert proposed.status_code == 200
        assert proposed.json()["proposed_text"]

        decided = client.post(
            f"/contracts/{contract_id}/negotiations/{item_id}/decide",
            headers=headers, json={"decision": "accepted"})
        assert decided.status_code == 200, decided.text
        assert decided.json()["status"] == "accepted"

        updated = client.get(f"/contracts/{contract_id}/sections",
                             headers=headers).json()
        updated_section = next(s for s in updated if s["id"] == section["id"])
        assert "Amended by negotiation" in updated_section["content"]

        rejected = client.post(
            f"/contracts/{contract_id}/negotiations/{item_id}/decide",
            headers=headers, json={"decision": "accepted"})
        assert rejected.status_code in (200, 400)
        items = client.get(f"/contracts/{contract_id}/negotiations",
                           headers=headers).json()
        assert items[0]["status"] in ("accepted", "rejected", "escalated")


class TestExport:
    def test_export_gated_by_approval_and_blockers(self, client):
        headers, contract_id = make_generated_contract(client)

        # Final format blocked without approval
        resp = client.post(f"/contracts/{contract_id}/export",
                           headers=headers, json={"format": "docx"})
        assert resp.status_code == 400, resp.text
        assert "approval" in resp.text.lower()

        # HTML preview allowed without approval
        resp = client.post(f"/contracts/{contract_id}/export",
                           headers=headers, json={"format": "html"})
        assert resp.status_code == 200, resp.text
        export_id = resp.json()["export_id"]

        content = client.get(
            f"/contracts/{contract_id}/export/{export_id}/content",
            headers=headers)
        assert content.status_code == 200
        assert b"<!DOCTYPE html>" in content.content

    def test_real_docx_pdf_bytes_produced(self, client):
        headers, contract_id = make_generated_contract(client)
        client.post(f"/contracts/{contract_id}/approve", headers=headers,
                    json={"notes": "ok"})

        docx = client.post(f"/contracts/{contract_id}/export",
                           headers=headers, json={"format": "docx"})
        assert docx.status_code == 200, docx.text
        docx_content = client.get(
            f"/contracts/{contract_id}/export/{docx.json()['export_id']}/content",
            headers=headers)
        assert docx_content.content[:2] == b"PK"  # ZIP/DOCX magic

        pdf = client.post(f"/contracts/{contract_id}/export",
                          headers=headers, json={"format": "pdf"})
        assert pdf.status_code == 200, pdf.text
        pdf_content = client.get(
            f"/contracts/{contract_id}/export/{pdf.json()['export_id']}/content",
            headers=headers)
        assert pdf_content.content[:4] == b"%PDF"  # PDF magic

    def test_export_blocked_by_open_blockers(self, client):
        headers, contract_id = make_generated_contract(client)
        client.post(f"/contracts/{contract_id}/validate", headers=headers)
        resp = client.post(f"/contracts/{contract_id}/export",
                           headers=headers, json={"format": "html"})
        assert resp.status_code == 400, resp.text
        assert "blocker" in resp.text.lower()

    def test_audit_trail(self, client):
        headers, contract_id = make_generated_contract(client)
        events = client.get(f"/contracts/{contract_id}/audit",
                            headers=headers).json()
        types = {e["event_type"] for e in events}
        assert "generation" in types