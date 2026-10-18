from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from apps.api.app.modules.core.db import get_session
from apps.api.app.modules.core.models import ValidationFinding
from apps.api.app.modules.validation.service import (
    run_deterministic_validation, run_validation, DETERMINISTIC_RULES
)

router = APIRouter(prefix="/validation", tags=["validation"])


@router.post("/{contract_id}")
def validate_contract(
    contract_id: int,
    include_ai: bool = False,
    session: Session = Depends(get_session),
):
    """Run validation on a contract."""
    result = run_validation(session, contract_id, include_ai=include_ai)
    if result.get("status") == "failed":
        raise HTTPException(status_code=404, detail=result.get("message", "Validation failed"))
    return result


@router.get("/{contract_id}/findings")
def get_findings(
    contract_id: int,
    session: Session = Depends(get_session),
):
    """Get all validation findings for a contract."""
    statement = select(ValidationFinding).where(ValidationFinding.contract_id == contract_id)
    findings = session.exec(statement).all()
    return {"findings": findings, "count": len(findings)}


@router.get("/{contract_id}/summary")
def get_validation_summary(
    contract_id: int,
    session: Session = Depends(get_session),
):
    """Get validation summary for a contract."""
    statement = select(ValidationFinding).where(ValidationFinding.contract_id == contract_id)
    findings = session.exec(statement).all()

    blockers = sum(1 for f in findings if f.severity == "blocker")
    high_risks = sum(1 for f in findings if f.severity == "high")
    warnings = sum(1 for f in findings if f.severity == "warning")

    total_checks = len(DETERMINISTIC_RULES)  # deterministic rule count
    passed = max(0, total_checks - (blockers + high_risks))

    return {
        "status": "needs_review" if blockers > 0 else "valid",
        "blockers": blockers,
        "high_risks": high_risks,
        "warnings": warnings,
        "passed_checks": passed,
        "total_checks": total_checks,
    }


@router.post("/{contract_id}/risk-analysis")
def risk_analysis(
    contract_id: int,
    session: Session = Depends(get_session),
):
    """Perform risk analysis on a contract."""
    statement = select(ValidationFinding).where(ValidationFinding.contract_id == contract_id)
    findings = session.exec(statement).all()

    def _items(sev: str) -> List[Dict[str, str]]:
        return [
            {
                "title": f.title,
                "explanation": f.explanation,
                "recommendation": f.recommendation or "",
            }
            for f in findings
            if f.severity == sev
        ]

    return {
        "blockers": _items("blocker"),
        "high_risks": _items("high"),
        "warnings": _items("warning"),
    }
