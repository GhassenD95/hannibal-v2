from . import LLMProvider, EmbeddingProvider, RerankerProvider


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
            for ev in retrieved_evidence[:3]:  # Top 3
                sections.append(f"  - {ev.get('title', 'Unknown')}")
                sections.append(f"    Jurisdiction: {ev.get('jurisdiction', '?')}")
                sections.append(f"    Relevance: {ev.get('relevanceReason', '?')}")
        
        return "\n".join(sections)
    
    def _validate_output(self, output: dict, schema: dict) -> dict:
        """Validate generation output against schema."""
        # Basic validation - in production would use pydantic
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