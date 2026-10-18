"""Comprehensive tests for Hannibal V2."""

import pytest
from fastapi.testclient import TestClient
from apps.api.app.main import app


class TestAPIStructure:
    """Test that the API structure is correct."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = TestClient(app)

    def test_root_endpoint(self):
        """Test the root endpoint returns correct response."""
        resp = self.client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert "Hannibal" in data["message"] or "API" in data["message"]


class TestInformationCollector:
    """Test the information collector module."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = TestClient(app)

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


class TestRAG:
    """Test the RAG and evidence retrieval module."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = TestClient(app)

    def test_search_sources(self):
        """Test legal source search."""
        resp = self.client.post("/rag/search", json={
            "query": "service agreement Morocco",
            "jurisdiction": "MA",
            "limit": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "count" in data

    def test_get_evidence(self):
        """Test evidence retrieval for a section."""
        resp = self.client.post("/rag/evidence/Payment", json={
            "jurisdiction": "MA",
            "contract_type": "service_agreement",
            "limit": 3,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "evidence" in data


class TestContractPlanner:
    """Test the contract planner module."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = TestClient(app)

    def test_create_plan(self):
        """Test contract plan creation."""
        resp = self.client.post("/planner/1", json={
            "section_titles": ["Parties", "Scope", "Payment"],
            "clause_selections": [{
                "section_id": "payment",
                "clause_id": 1,
                "clause_title": "Confidentiality",
                "clause_type": "mandatory"
            }],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] is not None
        assert data["status"] == "pending"

    def test_get_plan(self):
        """Test getting a contract plan."""
        resp = self.client.get("/planner/1")
        assert resp.status_code == 200


class TestValidation:
    """Test the validation and risk engine."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = TestClient(app)

    def test_validate_contract(self):
        """Test contract validation."""
        resp = self.client.post("/validation/1")
        assert resp.status_code == 200
        data = resp.json()
        assert "findings_count" in data

    def test_validation_summary(self):
        """Test validation summary."""
        resp = self.client.get("/validation/1/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data

    def test_risk_analysis(self):
        """Test risk analysis."""
        resp = self.client.post("/validation/1/risk-analysis")
        assert resp.status_code == 200
        data = resp.json()
        assert "blockers" in data


class TestRendering:
    """Test the document rendering module."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = TestClient(app)

    def test_validate_export(self):
        """Test export validation."""
        resp = self.client.post("/rendering/1/validate-export", json={
            "version_number": 1,
            "format": "html",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "can_export" in data

    def test_available_formats(self):
        """Test available export formats."""
        resp = self.client.get("/rendering/1/formats")
        assert resp.status_code == 200
        data = resp.json()
        assert "formats" in data


class TestAIProviders:
    """Test the AI provider module."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = TestClient(app)

    def test_ai_extract(self):
        """Test AI contract request extraction."""
        resp = self.client.post("/ai/extract", json={
            "description": "I need a 12-month service agreement in Morocco for 20,000 MAD",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "contract_type" in data

    def test_ai_generate_section(self):
        """Test AI section generation."""
        resp = self.client.post("/ai/generate-section", json={
            "section_title": "Payment",
            "contract_facts": {"amount": "20000", "currency": "MAD"},
            "approved_clauses": [1],
            "retrieved_evidence": [{"id": "ev_001"}],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "section_title" in data

    def test_ai_review_draft(self):
        """Test AI draft review."""
        resp = self.client.post("/ai/review-draft", json={
            "validation_findings": [{"severity": "blocker", "title": "Test"}],
            "risk_findings": [{"severity": "high", "title": "Test"}],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_status" in data

    def test_ai_analyze_negotiation(self):
        """Test AI negotiation analysis."""
        resp = self.client.post("/ai/analyze-negotiation", json={
            "baseline_clause": "Standard clause",
            "counterparty_clause": "Modified clause",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "risk_assessment" in data

    def test_ai_embed_query(self):
        """Test AI query embedding."""
        resp = self.client.post("/ai/embed-query", json={
            "text": "service agreement Morocco",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "embedding" in data

    def test_ai_rerank(self):
        """Test AI chunk reranking."""
        resp = self.client.post("/ai/rerank", json={
            "query": "payment obligations",
            "chunks": [
                {"content": "Payment clause", "source_id": "src_001"},
            ],
            "jurisdiction": "MA",
            "contract_type": "service_agreement",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "reranked_chunks" in data