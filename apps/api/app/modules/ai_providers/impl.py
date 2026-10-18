from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol defining the LLM provider interface."""
    
    async def extract_contract_request(self, input: dict) -> dict: ...
    async def generate_section(self, input: dict) -> dict: ...
    async def review_draft(self, input: dict) -> dict: ...
    async def analyze_negotiation(self, input: dict) -> dict: ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol defining the embedding provider interface."""
    
    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    async def embed_query(self, text: str) -> list[float]: ...


@runtime_checkable
class RerankerProvider(Protocol):
    """Protocol for authority-aware reranking of retrieved evidence."""
    
    async def rerank(
        self, query: str, candidate_chunks: list[dict],
        jurisdiction: str, contract_type: str
    ) -> list[dict]: ...


class BaseLLMProvider:
    """Base LLM provider with common functionality."""
    
    def __init__(
        self, 
        model_name: str = "default",
        temperature: float = 0.0,
        provider: str = "openai"
    ):
        self.model_name = model_name
        self.temperature = temperature
        self.provider = provider
        self.prompt_version = "1.0.0"
        self.token_usage = 0
        self.latency = 0
    
    def _build_context_package(
        self,
        contract_facts: dict,
        contract_plan: dict,
        approved_clauses: list,
        retrieved_evidence: list
    ) -> str:
        """Build the context package for generation prompts."""
        sections = []
        
        if contract_facts:
            sections.append("CONTRACT FACTS")
            for key, value in contract_facts.items():
                sections.append(f"  {key}: {value}")
        
        if contract_plan:
            sections.append("CONTRACT PLAN")
            sections.append(f"  Required sections: {contract_plan.get('sections_required', [])}")
            sections.append(f"  Selected clauses: {len(approved_clauses)} clauses")
        
        if retrieved_evidence:
            sections.append("RETRIEVED EVIDENCE")
            for ev in retrieved_evidence[:3]:
                sections.append(f"  - {ev.get('title', 'Unknown')}")
                sections.append(f"    Jurisdiction: {ev.get('jurisdiction', '?')}")
                sections.append(f"    Relevance: {ev.get('relevanceReason', '?')}")
        
        return "\n".join(sections)
    
    def _validate_output(self, output: dict, schema: dict) -> dict:
        """Validate generation output against schema."""
        required = schema.get("required", [])
        for field in required:
            if field not in output:
                output[field] = None
        return output


class BaseEmbeddingProvider:
    """Base embedding provider."""
    
    def __init__(self, model_name: str = "default", provider: str = "openai"):
        self.model_name = model_name
        self.provider = provider


class BaseRerankerProvider:
    """Base reranker provider for authority-aware ranking."""
    
    def __init__(self, model_name: str = "default"):
        self.model_name = model_name


# Concrete implementations

class MockLLMProvider:
    """Mock LLM provider for testing and development."""
    
    def __init__(self, model_name: str = "mock", temperature: float = 0.0):
        self.model_name = model_name
        self.temperature = temperature
        self.call_count = 0
    
    async def extract_contract_request(self, input: dict) -> dict:
        """Mock extraction."""
        self.call_count += 1
        
        description = input.get("description", "")
        desc_lower = description.lower()
        
        if "nda" in desc_lower:
            contract_type = "nda"
        elif "service" in desc_lower:
            contract_type = "service_agreement"
        else:
            contract_type = "service_agreement"
        
        if "maroc" in desc_lower or "morocco" in desc_lower:
            jurisdiction = "MA"
        elif "tunisie" in desc_lower or "tunisia" in desc_lower:
            jurisdiction = "TN"
        elif "france" in desc_lower:
            jurisdiction = "FR"
        else:
            jurisdiction = "MA"
        
        import re
        facts = {}
        if "month" in desc_lower:
            m = re.search(r'(\d+)\s*month', desc_lower)
            if m:
                facts["duration"] = f"{m.group(1)} months"
        if "MAD" in desc_lower or "dh" in desc_lower or "tnd" in desc_lower or "dt " in desc_lower:
            m = re.search(r'(\d[\d,]*)\s*(MAD|dh|TND|DT)', desc_lower)
            if m:
                facts["amount"] = m.group(1).replace(",", "")
        
        return {
            "contract_type": contract_type,
            "jurisdiction": jurisdiction,
            "facts": facts,
            "assumptions": ["Extracted from natural language description"],
            "missing_info": [],
            "token_usage": 50 * self.call_count,
            "latency_ms": 200 * self.call_count
        }
    
    async def generate_section(self, input: dict) -> dict:
        """Deterministic, structured section generation.

        Content is drawn only from the approved clause library; evidence ids
        reference approved+effective sources; missing support => abstain
        (needs_review/unsupported), never fabricated.
        """
        self.call_count += 1

        section_title = input.get("section_title", "Unknown Section")
        contract_facts = input.get("contract_facts", {})
        approved_clauses = input.get("approved_clauses", [])  # list[dict]
        retrieved_evidence = input.get("retrieved_evidence", [])  # list[dict]
        is_required = input.get("is_required", True)

        clause = None
        for candidate in approved_clauses:
            if isinstance(candidate, dict) and candidate.get("content"):
                clause = candidate
                break
        facts_used = []
        if clause is None or not clause.get("content"):
            return {
                "section_title": section_title,
                "content": "",
                "clause_ids": [],
                "evidence_ids": [],
                "facts_used": [],
                "assumptions": [],
                "abstain_reason": (
                    "No approved clause or approved source available for this section"
                ),
                "status": "needs_review" if is_required else "unsupported",
                "token_usage": 0,
                "latency_ms": 0,
            }

        content = clause["content"]
        for key, value in contract_facts.items():
            if key.lower() in content.lower() or str(value)[:6] in content:
                facts_used.append(key)
        evidence_used = []
        for ev in retrieved_evidence[:3]:
            source_id = ev.get("source_id")
            if source_id and source_id not in evidence_used:
                evidence_used.append(str(source_id))

        return {
            "section_title": section_title,
            "content": content,
            "clause_ids": [clause["id"]] if "id" in clause else
                          (clause.get("clause_ids") or []),
            "evidence_ids": evidence_used,
            "facts_used": facts_used,
            "assumptions": ["Content drawn from approved clause library"],
            "abstain_reason": None,
            "status": "supported",
            "token_usage": 100 * self.call_count,
            "latency_ms": 150 * self.call_count,
        }
    
    async def review_draft(self, input: dict) -> dict:
        """Mock draft review."""
        self.call_count += 1
        
        validation_findings = input.get("validation_findings", [])
        risk_findings = input.get("risk_findings", [])
        
        blockers = [f for f in validation_findings if f.get("severity") == "blocker"]
        high_risks = [f for f in risk_findings if f.get("severity") == "high"]
        
        return {
            "overall_status": "blockers_exist" if blockers else 
                             "high_risks" if high_risks else "valid",
            "blocker_count": len(blockers),
            "high_risk_count": len(high_risks),
            "warning_count": len([f for f in validation_findings if f.get("severity") == "warning"]),
            "requires_human_review": len(blockers) > 0 or len(high_risks) > 0,
            "token_usage": 30 * self.call_count,
            "latency_ms": 100 * self.call_count
        }
    
    async def analyze_negotiation(self, input: dict) -> dict:
        """Mock negotiation analysis."""
        self.call_count += 1
        
        baseline = input.get("baseline_clause", "Standard clause")
        counterparty = input.get("counterparty_clause", "Counterparty clause")
        
        return {
            "baseline_clause": baseline,
            "counterparty_clause": counterparty,
            "deviations": ["Content difference detected"] if baseline != counterparty else [],
            "risk_assessment": "medium" if baseline != counterparty else "low",
            "recommendation": "Review and decide acceptance",
            "requires_human_decision": baseline != counterparty,
            "token_usage": 40 * self.call_count,
            "latency_ms": 120 * self.call_count
        }


class MockEmbeddingProvider:
    """Mock embedding provider for testing."""
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
    
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Mock document embeddings."""
        return [[0.1] * self.dimension for _ in texts]
    
    async def embed_query(self, text: str) -> list[float]:
        """Mock query embedding."""
        return [0.1] * self.dimension


class MockRerankerProvider:
    """Mock reranker for testing."""
    
    async def rerank(
        self, 
        query: str, 
        candidate_chunks: list[dict],
        jurisdiction: str,
        contract_type: str
    ) -> list[dict]:
        """Mock reranking."""
        reranked = []
        for i, chunk in enumerate(candidate_chunks):
            score = 1.0 - (i * 0.1)
            if score < 0:
                score = 0
            
            reranked.append({
                **chunk,
                "relevance_score": max(score, 0),
                "authority_rating": "official" if i == 0 else "secondary",
                "rerank_rank": i + 1
            })
        
        reranked.sort(key=lambda x: x["relevance_score"], reverse=True)
        return reranked


# LLMProvider protocol instance - for type checking only
llm_provider_protocol = LLMProvider

# EmbeddingProvider protocol instance
embedding_provider_protocol = EmbeddingProvider

# RerankerProvider protocol instance
reranker_provider_protocol = RerankerProvider


# Export for easy import
__all__ = [
    "MockLLMProvider",
    "MockEmbeddingProvider", 
    "MockRerankerProvider",
    "BaseLLMProvider",
    "BaseEmbeddingProvider",
    "BaseRerankerProvider",
    "llm_provider_protocol",
    "embedding_provider_protocol",
    "reranker_provider_protocol"
]