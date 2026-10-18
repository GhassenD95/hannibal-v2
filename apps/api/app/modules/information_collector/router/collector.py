from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from apps.api.app.modules.core.db import get_session
from apps.api.app.modules.core.models import ContractRequest, CollectionProgress
from apps.api.app.modules.information_collector.schemas import (
    ExtractRequest, ValidateFieldRequest, ProgressUpdateRequest, FieldValidation
)
from apps.api.app.modules.information_collector.service import (
    collect_from_natural_language, get_contract_request,
    update_step_progress, validate_field, normalize_contract_type, normalize_jurisdiction
)

router = APIRouter(prefix="/information-collector", tags=["information-collector"])


@router.post("/extract", response_model=ContractRequest)
def extract_from_description(
    payload: ExtractRequest,
    session: Session = Depends(get_session)
):
    """Extract contract request from natural language description."""
    ct = normalize_contract_type(payload.contract_type or "")
    jd = normalize_jurisdiction(payload.jurisdiction or "")

    request = collect_from_natural_language(payload.description, payload.user_id, session)

    if ct:
        request.contract_type = ct
    if jd:
        request.jurisdiction = jd
    if ct or jd:
        session.add(request)
        session.commit()
        session.refresh(request)

    return request


@router.post("/validate/{field_name}")
def validate_field_endpoint(
    field_name: str,
    payload: ValidateFieldRequest,
    session: Session = Depends(get_session)
):
    """Validate a field and return any issues."""
    result = validate_field(session, None, field_name, payload.field_value)
    if result:
        return {"has_issue": True, "validation": result}
    return {"has_issue": False}


@router.get("/{request_id}", response_model=ContractRequest)
def get_request(
    request_id: int,
    session: Session = Depends(get_session)
):
    request = get_contract_request(session, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Contract request not found")
    return request


@router.get("/{request_id}/progress")
def get_progress(
    request_id: int,
    session: Session = Depends(get_session)
):
    """Get collection progress for all steps."""
    statement = select(CollectionProgress).where(
        CollectionProgress.contract_request_id == request_id
    )
    result = session.exec(statement)
    return result.all()


@router.post("/{request_id}/progress/{step_name}")
def update_progress(
    request_id: int,
    step_name: str,
    payload: ProgressUpdateRequest,
    session: Session = Depends(get_session)
):
    """Update progress for a specific step."""
    return update_step_progress(
        session, request_id, step_name,
        payload.completed, payload.field_count, payload.required_count
    )
