from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from apps.api.app.modules.core.db import get_session
from apps.api.app.modules.rag.service import search_sources, get_evidence_for_section, validate_source_status


class SearchRequest(BaseModel):
    """Body for POST /rag/search."""
    query: str
    jurisdiction: Optional[str] = None
    contract_type: Optional[str] = None
    language: Optional[str] = None
    limit: int = 10


class EvidenceRequest(BaseModel):
    """Body for POST /rag/evidence/{section_title}."""
    jurisdiction: str
    contract_type: str
    limit: int = 5


router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/search")
def search(
    payload: SearchRequest,
    session: Session = Depends(get_session)
):
    """Search legal sources."""
    results = search_sources(
        session,
        query=payload.query,
        jurisdiction=payload.jurisdiction,
        contract_type=payload.contract_type,
        language=payload.language,
        limit=payload.limit
    )
    return {"results": results, "count": len(results)}


@router.post("/evidence/{section_title}")
def get_evidence(
    section_title: str,
    payload: EvidenceRequest,
    session: Session = Depends(get_session)
):
    """Get evidence for a contract section."""
    evidence = get_evidence_for_section(
        session,
        section_title=section_title,
        jurisdiction=payload.jurisdiction,
        contract_type=payload.contract_type,
        limit=payload.limit
    )
    return {"evidence": evidence, "count": len(evidence)}


@router.post("/validate/{source_id}")
def validate_source(
    source_id: int,
    session: Session = Depends(get_session)
):
    """Validate a source status."""
    result = validate_source_status(session, source_id)
    if result["status"] != "valid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    return {"status": "valid"}
