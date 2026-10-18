from typing import Optional, List, Dict
from pydantic import BaseModel


class ContractRequestCreate(BaseModel):
    name: str
    description: Optional[str] = None
    contract_type: str
    jurisdiction: str = "MA"
    language: str = "fr"
    mode: str = "guided"  # guided | ai
    facts: Dict[str, str] = {}
    selected_clauses: List[int] = []
    evidence_ids: List[str] = []


class InterpretRequest(BaseModel):
    description: str


class ContractUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class SectionCreate(BaseModel):
    title: str
    order_index: int


class SectionUpdate(BaseModel):
    content: Optional[str] = None
    title: Optional[str] = None
    status: Optional[str] = None
    clause_ids: Optional[List[int]] = None
    evidence_ids: Optional[List[str]] = None
    facts_used: Optional[List[str]] = None