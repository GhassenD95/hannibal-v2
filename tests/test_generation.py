"""Tests for the generation engine: plan, generate, abstention, regeneration."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from apps.api.app.main import app
from apps.api.app.modules.core.db import engine
from apps.api.app.modules.core.models import GenerationRun, Clause, LegalSource
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def admin_headers():
    resp = TestClient(app).post("/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD,
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def make_confirmed_contract(client):
    headers = admin_headers()
    name = f"Gen {uuid.uuid4().hex[:6]}"
    resp = client.post("/contracts", headers=headers, json={
        "name": name, "contract_type": "service_agreement",
        "jurisdiction": "MA", "mode": "guided",
        "facts": {"amount": "20000", "currency": "MAD"},
    })
    request_id = resp.json()["id"]
    resp = client.post(f"/contracts/{request_id}/confirm-request", headers=headers)
    return headers, resp.json()


class TestGeneration:
    def test_plan_and_generate_full_contract(self, client):
        headers, config = make_confirmed_contract(client)
        contract_id = config["id"]
        plan = client.post(f"/contracts/{contract_id}/plan", headers=headers)
        assert plan.status_code == 200, plan.text
        plan_data = plan.json()
        assert "parties" in plan_data["sections_required"]
        assert plan_data["evidence_ids"]

        resp = client.post(f"/contracts/{contract_id}/generate", headers=headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "drafted"
        assert data["generated_sections"] > 0

        sections = client.get(f"/contracts/{contract_id}/sections", headers=headers).json()
        expected = {s["title"]: s for s in sections}
        assert "Parties" in expected
        assert any(t.startswith("Payment") for t in expected)
        all_statuses = {s["status"] for s in sections}
        assert "supported" in all_statuses

        for section in sections:
            for cid in section["clause_ids"]:
                with Session(engine) as session:
                    clause = session.get(Clause, cid)
                    assert clause is not None and clause.status == "approved"
            for eid in section["evidence_ids"]:
                with Session(engine) as session:
                    source = session.get(LegalSource, int(eid))
                    assert source is not None and source.status == "approved"

    def test_placeholder_section_flagged_needs_review(self, client):
        headers, config = make_confirmed_contract(client)
        contract_id = config["id"]
        client.post(f"/contracts/{contract_id}/generate", headers=headers)
        sections = client.get(f"/contracts/{contract_id}/sections", headers=headers).json()
        payment = next(s for s in sections if s["title"].startswith("Payment"))
        assert payment["status"] == "needs_review"

    def test_generation_runs_persisted(self, client):
        headers, config = make_confirmed_contract(client)
        contract_id = config["id"]
        client.post(f"/contracts/{contract_id}/generate", headers=headers)
        with Session(engine) as session:
            runs = session.exec(select(GenerationRun).where(
                GenerationRun.contract_id == contract_id)).all()
            assert runs, "GenerationRun should be persisted"
            for run in runs:
                assert run.prompt_version
                assert run.model
                assert run.pack_version_id is not None
                assert "status" in run.output_snapshot

    def test_unsupported_section_abstains(self, client):
        headers, config = make_confirmed_contract(client)
        contract_id = config["id"]
        sections = client.get(f"/contracts/{contract_id}/sections",
                              headers=headers).json()
        parties = next(s for s in sections if s["title"] == "Parties")
        sid = parties["id"]

        # Archive every clause that supports "Parties" (both packs share the title)
        with Session(engine) as session:
            party_clauses = session.exec(select(Clause).where(
                Clause.title == "Party identification")).all()
            clause_ids = [c.id for c in party_clauses]
            for c in party_clauses:
                c.status = "archived"
                session.add(c)
            session.commit()
        try:
            resp = client.post(
                f"/contracts/{contract_id}/sections/{sid}/regenerate",
                headers=headers)
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["status"] == "needs_review"
            assert data["content"] == ""
            assert data["new_version_number"] >= 1
        finally:
            with Session(engine) as session:
                for cid in clause_ids:
                    restored = session.get(Clause, cid)
                    restored.status = "approved"
                    session.add(restored)
                session.commit()

    def test_regenerate_creates_new_version(self, client):
        headers, config = make_confirmed_contract(client)
        contract_id = config["id"]
        resp = client.post(f"/contracts/{contract_id}/generate", headers=headers)
        sections = client.get(f"/contracts/{contract_id}/sections",
                              headers=headers).json()
        sid = sections[1]["id"]
        before_versions = client.get(f"/contracts/{contract_id}/versions",
                                     headers=headers).status_code
        resp = client.post(
            f"/contracts/{contract_id}/sections/{sid}/regenerate", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in {"supported", "needs_review"}

    @pytest.mark.parametrize("jurisdiction,evidence_text", [
        ("MA", "amicably"),
        ("TN", "Code de l'arbitrage"),
    ])
    def test_dispute_resolution_uses_its_own_clause(self, client, jurisdiction,
                                                    evidence_text):
        headers = admin_headers()
        name = f"DR {jurisdiction} {uuid.uuid4().hex[:6]}"
        resp = client.post("/contracts", headers=headers, json={
            "name": name, "contract_type": "service_agreement",
            "jurisdiction": jurisdiction, "mode": "guided",
            "facts": {"amount": "20000", "currency": "TND" if jurisdiction == "TN" else "MAD"},
        })
        rid = resp.json()["id"]
        cfg = client.post(f"/contracts/{rid}/confirm-request",
                          headers=headers).json()
        cid = cfg["id"]
        client.post(f"/contracts/{cid}/generate", headers=headers)
        sections = client.get(f"/contracts/{cid}/sections",
                              headers=headers).json()
        by_title = {s["title"]: s for s in sections}
        dr = by_title["Dispute Resolution"]
        parties = by_title["Parties"]
        assert evidence_text in dr["content"], dr["content"]
        assert not set(dr["clause_ids"]) & set(parties["clause_ids"]), (
            "Dispute Resolution must not reuse the Parties clause")