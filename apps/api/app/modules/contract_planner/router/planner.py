from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from apps.api.app.modules.core.db import get_session
from apps.api.app.modules.core.models import ContractPlan, SectionDecision
from apps.api.app.modules.contract_planner.schemas import CreatePlanRequest, DecisionRequest
from apps.api.app.modules.contract_planner.service import (
    create_contract_plan, update_section_decision,
    get_plan, get_section_decisions
)

router = APIRouter(prefix="/planner", tags=["planner"])


@router.post("/{contract_id}", response_model=ContractPlan)
def create_plan(
    contract_id: int,
    payload: CreatePlanRequest,
    session: Session = Depends(get_session),
):
    """Create a contract plan for a contract."""
    plan = create_contract_plan(
        session, contract_id, payload.section_titles, payload.clause_selections
    )
    return plan


@router.get("/{contract_id}", response_model=ContractPlan)
def get_plan_endpoint(
    contract_id: int,
    session: Session = Depends(get_session),
):
    """Get the contract plan for a contract."""
    plan = get_plan(session, contract_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Contract plan not found")
    return plan


@router.get("/{contract_id}/decisions", response_model=List[SectionDecision])
def get_decisions(
    contract_id: int,
    session: Session = Depends(get_session),
):
    """Get all section decisions for a contract."""
    decisions = get_section_decisions(session, contract_id)
    return decisions


@router.post("/{contract_id}/decision", response_model=SectionDecision)
def make_decision(
    contract_id: int,
    payload: DecisionRequest,
    session: Session = Depends(get_session),
):
    """Make a decision on a contract section."""
    decision_obj = update_section_decision(
        session, contract_id, payload.section_id, payload.decision,
        payload.selected_clause_id, payload.rationale
    )
    return decision_obj
