"""Extended validation rule tests: placeholders, pack.match, source/clause status."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from apps.api.app.main import app
from apps.api.app.modules.core.db import engine
from apps.api.app.modules.core.models import Contract
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def admin_headers():
    resp = TestClient(app).post("/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD,
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def make_contract(session: Session, contract_type="service_agreement") -> int:
    contract = Contract(
        name=f"Validation target {uuid.uuid4().hex[:6]}",
        description="target for validation",
        contract_type=contract_type,
        jurisdiction="MA",
        language="fr",
        status="draft",
        organization_id=1,
    )
    session.add(contract)
    session.commit()
    session.refresh(contract)
    contract_id = contract.id
    return contract_id


class TestPlaceholderRule:
    def test_placeholder_text_yields_blocker(self, client):
        from apps.api.app.modules.core.models import ContractSection
        with Session(engine) as session:
            contract_id = make_contract(session)
            session.add(ContractSection(
                contract_id=contract_id, title="Payment",
                content="Pay [Amount] in full.", order_index=1,
                status="needs_review"))
            session.commit()
        resp = client.post(f"/contracts/{contract_id}/validate",
                           headers=admin_headers())
        assert resp.status_code == 200
        blockers = [f for f in resp.json()["findings"]
                    if f["rule_id"] == "placeholder.check"]
        assert blockers, "unresolved placeholder should be a blocker"
        assert "Payment" in blockers[0]["title"]


class TestPackMatchRule:
    def test_unsupported_type_yields_pack_match_blocker(self, client):
        with Session(engine) as session:
            contract_id = make_contract(session, contract_type="franchise")
        resp = client.post(f"/contracts/{contract_id}/validate",
                           headers=admin_headers())
        blockers = [f for f in resp.json()["findings"]
                    if f["rule_id"] == "pack.match"]
        assert blockers, "no active pack should be a pack.match blocker"


class TestSourceAndClauseStatus:
    def test_nonapproved_evidence_yields_source_status(self, client):
        from apps.api.app.modules.core.models import ContractSection
        with Session(engine) as session:
            contract_id = make_contract(session)
            session.add(ContractSection(
                contract_id=contract_id, title="Payment",
                content="Full content no placeholders.", order_index=1,
                status="supported",
                evidence_ids=["999999"], clause_ids=[999999]))
            session.commit()
        resp = client.post(f"/contracts/{contract_id}/validate",
                           headers=admin_headers())
        source_issues = [f for f in resp.json()["findings"]
                         if f["rule_id"] == "source.status"]
        clause_issues = [f for f in resp.json()["findings"]
                         if f["rule_id"] == "clause.status"]
        assert source_issues and clause_issues

    def test_validation_supersedes_old_findings(self, client):
        with Session(engine) as session:
            contract_id = make_contract(session)
        first = client.post(f"/contracts/{contract_id}/validate",
                            headers=admin_headers())
        second = client.post(f"/contracts/{contract_id}/validate",
                             headers=admin_headers())
        assert first.status_code == second.status_code == 200
        summary = client.get(f"/contracts/{contract_id}/validation/summary",
                             headers=admin_headers()).json()
        assert "blockers" in summary
        assert summary["total_checks"] > 0