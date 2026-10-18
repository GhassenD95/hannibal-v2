from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol defining the LLM provider interface."""
    
    async def extract_contract_request(
        self, input: dict
    ) -> dict:
        """Extract structured contract request from natural language input.
        
        Args:
            input: Raw user input (description, form data, etc.)
            
        Returns:
            ContractExtraction with structured facts, contract type, jurisdiction, etc.
        """
        ...
    
    async def generate_section(
        self, input: dict
    ) -> dict:
        """Generate a structured contract section.
        
        Args:
            input: Section generation input including:
                - contract_facts: Confirmed facts from collector
                - contract_plan: ContractPlan from planner
                - approved_clauses: Selected approved clause IDs
                - retrieved_evidence: Evidence objects
                - generation_task: Description of the generation task
                - output_schema: JSON schema for output validation
            
        Returns:
            GeneratedSection with structured content, evidence IDs, assumptions
        """
        ...
    
    async def review_draft(
        self, input: dict
    ) -> dict:
        """Review a contract draft for consistency and legal issues.
        
        Args:
            input: Review input including:
                - contract_sections: All contract sections
                - validation_findings: From validation engine
                - risk_findings: From risk engine
                - contract_type: Type of contract
                - jurisdiction: Governing jurisdiction
            
        Returns:
            ReviewResult with structured findings, recommendations
        """
        ...
    
    async def analyze_negotiation(
        self, input: dict
    ) -> dict:
        """Analyze negotiation items against playbooks.
        
        Args:
            input: Negotiation analysis input including:
                - baseline_clause: Hannibal's preferred clause
                - counterparty_clause: Counterparty's proposed clause
                - contract_type: Type of contract
                - jurisdiction: Governing jurisdiction
                - playbook: Negotiation playbook to reference
            
        Returns:
            NegotiationAnalysis with deviation analysis, risk assessment, recommendation
        """
        ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol defining the embedding provider interface."""
    
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple documents for vector storage.
        
        Args:
            texts: List of document texts to embed
            
        Returns:
            List of embedding vectors (one per text)
        """
        ...
    
    async def embed_query(self, text: str) -> list[float]:
        """Embed a query vector for retrieval.
        
        Args:
            text: Query text to embed
            
        Returns:
            Embedding vector for the query
        """
        ...


@runtime_checkable
class RerankerProvider(Protocol):
    """Protocol for authority-aware reranking of retrieved evidence."""
    
    async def rerank(
        self, 
        query: str, 
        candidate_chunks: list[dict],
        jurisdiction: str,
        contract_type: str
    ) -> list[dict]:
        """Rerank retrieved evidence chunks by authority and relevance.
        
        Args:
            query: Original user query
            candidate_chunks: Candidate evidence chunks from retrieval
            jurisdiction: Governing jurisdiction
            contract_type: Type of contract
            
        Returns:
            Reranked chunks with relevance scores and authority ratings
        """
        ...