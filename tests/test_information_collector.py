"""Tests for the Information Collector module."""

import pytest
from fastapi.testclient import TestClient
from apps.api.app.main import app


class TestInformationCollector:
    """Test the information collector endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = TestClient(app)

    def test_root_endpoint(self):
        """Test the root endpoint."""
        resp = self.client.get("/")
        assert resp.status_code == 200
        assert "message" in resp.json()

    def test_extract_from_natural_language(self):
        """Test contract request extraction from natural language."""
        resp = self.client.post(
            "/information-collector/extract",
            json={
                "description": "I need a 12-month service agreement in Morocco for 20,000 MAD",
                "contract_type": "service_agreement",
                "jurisdiction": "MA",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["contract_type"] == "service_agreement"
        assert data["jurisdiction"] == "MA"
        assert "facts" in data

    def test_extract_nda(self):
        """Test NDA extraction from natural language."""
        resp = self.client.post(
            "/information-collector/extract",
            json={
                "description": "NDA between two companies for confidentiality",
                "contract_type": "nda",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["contract_type"] == "nda"

    def test_validate_field(self):
        """Test field validation."""
        resp = self.client.post(
            "/information-collector/validate/contract_type",
            json={"field_name": "contract_type", "field_value": ""},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_issue"] == True

    def test_progress_tracking(self):
        """Test collection progress tracking."""
        # Create a contract request first
        extract_resp = self.client.post(
            "/information-collector/extract",
            json={
                "description": "Service agreement",
                "contract_type": "service_agreement",
            },
        )
        request_id = extract_resp.json()["id"]

        # Update progress
        progress_resp = self.client.post(
            f"/information-collector/{request_id}/progress/basics",
            json={"completed": True, "field_count": 3, "required_count": 3},
        )
        assert progress_resp.status_code == 200
        data = progress_resp.json()
        assert data["completed"] == True