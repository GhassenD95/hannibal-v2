from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class PlanOut(BaseModel):
    id: int
    contract_id: int
    sections_required: List[str]
    sections_complete: List[str]
    selected_clauses: List[int]
    evidence_ids: List[str]
    unresolved_decisions: List[str]
    status: str


class GenerateOut(BaseModel):
    contract_id: int
    status: str
    generated_sections: int
    supported: int
    needs_review: int
    unsupported: int


class SectionRunOut(BaseModel):
    section_id: int
    title: str
    status: str
    content: str
    clause_ids: List[int]
    evidence_ids: List[str]
    facts_used: List[str]
    abstain_reason: Optional[str] = None