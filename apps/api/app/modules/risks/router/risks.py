from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from apps.api.app.modules.core.db import get_session
from apps.api.app.modules.core.models import Users, RiskFinding
from apps.api.app.modules.auth.deps import get_current_user
from apps.api.app.modules.risks.service import run_risk_analysis
from apps.api.app.modules.contracts import service as contracts_service

router = APIRouter(prefix="/risks", tags=["risks"])


@router.post("/{contract_id}")
async def analyze_risks(
    contract_id: int,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    try:
        result = await run_risk_analysis(session, user, contract_id)
    except contracts_service.OrgPermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except contracts_service.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result


@router.get("/{contract_id}")
def list_risks(
    contract_id: int,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    try:
        contracts_service.get_contract(session, user, contract_id)
    except contracts_service.OrgPermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except contracts_service.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    risks = session.exec(select(RiskFinding).where(
        RiskFinding.contract_id == contract_id).order_by(RiskFinding.id)).all()
    return [
        {"id": r.id, "title": r.title, "severity": r.severity,
         "explanation": r.explanation, "location": r.location,
         "recommendation": r.recommendation, "status": r.status,
         "section_id": r.section_id}
        for r in risks
    ]