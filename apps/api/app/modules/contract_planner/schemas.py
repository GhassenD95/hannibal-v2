from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel


class CreatePlanRequest(SQLModel):
    """Body for POST /planner/{contract_id}."""
    section_titles: List[str]
    clause_selections: List[Dict[str, Any]] = []


class DecisionRequest(SQLModel):
    """Body for POST /planner/{contract_id}/decision."""
    section_id: str
    decision: str  # "approved", "needs_decision", "unsupported"
    selected_clause_id: Optional[int] = None
    rationale: Optional[str] = None
