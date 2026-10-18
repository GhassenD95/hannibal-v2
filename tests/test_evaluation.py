"""Evaluation engine tests."""

import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient

from apps.api.app.main import app
from apps.api.app.modules.core.db import engine
from apps.api.app.modules.evaluation import service as evaluation
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


@pytest.fixture(scope="module", autouse=True)
def active_demo_packs():
    """Re-activate both demo packs.

    test_pack_validate_and_activate runs earlier in the suite and its
    activation demotes every other active pack to draft; restore the baseline
    (both packs active) so fixture selection is order-independent.
    """
    from tests.conftest import _ensure_active_pack

    _ensure_active_pack()


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def admin_headers():
    resp = TestClient(app).post("/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD,
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


METRIC_CATEGORIES = {
    "extraction", "retrieval", "planning", "generation", "validation", "system",
}


class TestFixturesEndpoint:
    def test_fixtures_loaded_from_file(self, client):
        resp = client.get("/admin/evaluation/fixtures", headers=admin_headers())
        assert resp.status_code == 200, resp.text
        fixtures = resp.json()
        assert fixtures and all(f["id"] for f in fixtures)


class TestEvaluationRun:
    def test_run_returns_documented_metric_keys(self, client):
        resp = client.post("/admin/evaluation/run", headers=admin_headers())
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["run_id"] > 0
        assert set(data["metrics"]) >= METRIC_CATEGORIES
        for category in METRIC_CATEGORIES:
            assert data["metrics"][category]
        assert "forbidden_claims_hit_rate" in data["metrics"]
        assert len(data["per_fixture"]) >= 2

    def test_run_persisted(self, client):
        client.post("/admin/evaluation/run", headers=admin_headers())
        runs = client.get("/admin/evaluation/runs", headers=admin_headers()).json()
        assert runs and runs[0]["total_fixtures"] >= 2
        assert runs[0]["metrics"]

    def test_evaluation_requires_admin(self, client):
        other = TestClient(app).post("/auth/login", json={
            "email": "reviewer@other.local", "password": "reviewer123",
        }).json()["access_token"]
        resp = client.post("/admin/evaluation/run", headers={
            "Authorization": f"Bearer {other}"})
        assert resp.status_code == 403


class TestForbiddenClaims:
    def test_detector_flags_forbidden_claim(self):
        hits = evaluation.detect_forbidden_claims(
            "The contract auto-renews. Auto-renewal without notice is asserted.",
            ["Auto-renewal without notice", "Unlimited liability"])
        assert hits == ["Auto-renewal without notice"]

    def test_forbidden_claim_in_input_raises_hit(self, client):
        from apps.api.app.modules.core.models import Users
        from sqlmodel import Session, select
        from apps.api.app.modules.auth.service import get_user_by_email

        with Session(engine) as session:
            user = get_user_by_email(session, ADMIN_EMAIL)
            fixture = {
                "id": f"fixture_forbidden_{uuid.uuid4().hex[:6]}",
                "name": "forbidden claim probe",
                "jurisdiction": "MA",
                "contractType": "service_agreement",
                "input": {
                    "description": (
                        "Agreement with a clause describing Auto-renewal "
                        "without notice between Alpha and Beta"),
                    "contract_type": "service_agreement",
                    "jurisdiction": "MA",
                },
                "expectedSections": ["Parties"],
                "requiredClauses": [],
                "expectedEvidence": [],
                "expectedRisks": [],
                "forbiddenClaims": ["Auto-renewal without notice"],
            }
            metrics = asyncio.run(
                evaluation.evaluate_fixture(session, user, fixture))
            assert metrics["forbidden_claims_hit"] == 1