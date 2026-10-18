from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlmodel import Session, select
from apps.api.app.modules.core.models import (
    Contract, Clause, LegalSource, ContractPlan, SectionDecision, ClauseSelection
)
from apps.api.app.modules.rag.service import get_evidence_for_section


def create_contract_plan(
    session: Session,
    contract_id: int,
    section_titles: List[str],
    clause_selections: List[Dict[str, Any]],
) -> ContractPlan:
    """Create a contract plan based on selected sections and clauses."""
    
    plan = ContractPlan(
        contract_id=contract_id,
        title=f"Plan for contract {contract_id}",
        description="Automatically generated contract planning",
        sections_required=section_titles,
        sections_complete=[],
        selected_clauses=[cs.get("clause_id") for cs in clause_selections],
        evidence_ids=[],
        unresolved_decisions=[],
        status="pending",
    )
    
    session.add(plan)
    session.commit()
    session.refresh(plan)
    
    # Assign clause selections
    for cs in clause_selections:
        clause_selection = ClauseSelection(
            contract_id=contract_id,
            section_id=cs.get("section_id", ""),
            clause_id=cs.get("clause_id", 0),
            clause_title=cs.get("clause_title", ""),
            clause_type=cs.get("clause_type", "optional"),
            reason=cs.get("reason", "Selected from approved clause library"),
        )
        session.add(clause_selection)
    
    # Get evidence for each section
    for section_title in section_titles:
        evidence = get_evidence_for_section(
            session,
            section_title=section_title,
            jurisdiction="MA",  # TODO: get from contract
            contract_type="service_agreement",  # TODO: get from contract
            limit=3,
        )
        # Link evidence to plan (dedupe source ids)
        if evidence:
            source_id = evidence[0].source_id
            if source_id not in plan.evidence_ids:
                plan.evidence_ids = [*plan.evidence_ids, source_id]
    
    session.commit()
    session.refresh(plan)
    
    return plan


def update_section_decision(
    session: Session,
    contract_id: int,
    section_id: str,
    decision: str,
    selected_clause_id: Optional[int] = None,
    rationale: Optional[str] = None,
) -> SectionDecision:
    """Update or create a section decision."""
    
    # Check if decision already exists
    statement = select(SectionDecision).where(
        SectionDecision.contract_id == contract_id,
        SectionDecision.section_id == section_id,
    )
    existing = session.exec(statement).first()
    
    if existing:
        existing.decision = decision
        existing.selected_clause_id = selected_clause_id
        existing.rationale = rationale
        existing.decided_at = datetime.utcnow()
        session.add(existing)
    else:
        existing = SectionDecision(
            contract_id=contract_id,
            section_id=section_id,
            section_title="",  # TODO: get section title
            decision=decision,
            selected_clause_id=selected_clause_id,
            assigned_evidence=[],
            rationale= rationale,
            decided_at=datetime.utcnow(),
        )
        session.add(existing)
    
    session.commit()
    session.refresh(existing)
    return existing


def get_plan(
    session: Session,
    contract_id: int,
) -> ContractPlan | None:
    """Get the contract plan for a contract."""
    statement = select(ContractPlan).where(ContractPlan.contract_id == contract_id)
    return session.exec(statement).first()


def get_section_decisions(
    session: Session,
    contract_id: int,
) -> List[SectionDecision]:
    """Get all section decisions for a contract."""
    statement = select(SectionDecision).where(SectionDecision.contract_id == contract_id)
    return session.exec(statement).all()