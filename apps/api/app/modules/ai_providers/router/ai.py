from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Body, HTTPException, status
from sqlmodel import Session
from ...core.db import get_session
from apps.api.app.modules.ai_providers.impl import (
    MockLLMProvider,
    MockEmbeddingProvider,
    MockRerankerProvider
)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/extract", response_model=dict)
async def extract_contract_request(
    data: dict = Body(...),
    use_mock: bool = True,
    session: Session = Depends(get_session),
):
    """Extract contract request from natural language description."""
    description = data.get("description", "")
    contract_type = data.get("contract_type")
    jurisdiction = data.get("jurisdiction")
    
    if not use_mock:
        raise HTTPException(status_code=501, detail="Only mock providers are configured")
    provider = MockLLMProvider()

    result = await provider.extract_contract_request({
        "description": description,
        "contract_type": contract_type,
        "jurisdiction": jurisdiction,
    })
    return result


@router.post("/generate-section", response_model=dict)
async def generate_section(
    data: dict = Body(...),
    use_mock: bool = True,
    session: Session = Depends(get_session),
):
    """Generate a contract section."""
    section_title = data.get("section_title", "")
    contract_facts = data.get("contract_facts", {})
    approved_clauses = data.get("approved_clauses", [])
    retrieved_evidence = data.get("retrieved_evidence", [])
    output_schema = data.get("output_schema", {})
    
    if not use_mock:
        raise HTTPException(status_code=501, detail="Only mock providers are configured")
    provider = MockLLMProvider()

    input_data = {
        "section_title": section_title,
        "contract_facts": contract_facts,
        "contract_plan": data.get("contract_plan", {}),
        "approved_clauses": approved_clauses or [],
        "retrieved_evidence": retrieved_evidence or [],
        "output_schema": output_schema or {},
    }
    
    result = await provider.generate_section(input_data)
    return result


@router.post("/review-draft", response_model=dict)
async def review_draft(
    data: dict = Body(...),
    use_mock: bool = True,
    session: Session = Depends(get_session),
):
    """Review a contract draft."""
    validation_findings = data.get("validation_findings", [])
    risk_findings = data.get("risk_findings", [])
    
    if not use_mock:
        raise HTTPException(status_code=501, detail="Only mock providers are configured")
    provider = MockLLMProvider()

    input_data = {
        "validation_findings": validation_findings,
        "risk_findings": risk_findings,
    }
    
    result = await provider.review_draft(input_data)
    return result


@router.post("/analyze-negotiation", response_model=dict)
async def analyze_negotiation(
    data: dict = Body(...),
    use_mock: bool = True,
    session: Session = Depends(get_session),
):
    """Analyze negotiation items."""
    baseline = data.get("baseline_clause", "")
    counterparty = data.get("counterparty_clause", "")
    playbook = data.get("playbook")
    
    if not use_mock:
        raise HTTPException(status_code=501, detail="Only mock providers are configured")
    provider = MockLLMProvider()

    input_data = {
        "baseline_clause": baseline,
        "counterparty_clause": counterparty,
        "playbook": playbook,
    }
    
    result = await provider.analyze_negotiation(input_data)
    return result


@router.post("/embed-query", response_model=dict)
async def embed_query(
    data: dict = Body(...),
    use_mock: bool = True,
    session: Session = Depends(get_session),
):
    """Embed a query vector."""
    text = data.get("text", "")
    
    if not use_mock:
        raise HTTPException(status_code=501, detail="Only mock providers are configured")
    provider = MockEmbeddingProvider()

    result = await provider.embed_query(text)
    return {"embedding": result, "dimension": len(result)}


@router.post("/rerank", response_model=dict)
async def rerank_chunks(
    data: dict = Body(...),
    use_mock: bool = True,
    session: Session = Depends(get_session),
):
    """Rerank retrieved evidence chunks."""
    query = data.get("query", "")
    chunks = data.get("chunks", [])
    jurisdiction = data.get("jurisdiction", "MA")
    contract_type = data.get("contract_type", "service_agreement")
    
    if not use_mock:
        raise HTTPException(status_code=501, detail="Only mock providers are configured")
    provider = MockRerankerProvider()

    result = await provider.rerank(query, chunks, jurisdiction, contract_type)
    return {"reranked_chunks": result}