from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session
from apps.api.app.modules.core.db import get_session
from apps.api.app.modules.core.models import ExportResult
from apps.api.app.modules.rendering.schemas import ExportRequest
from apps.api.app.modules.rendering.service import (
    validate_export, export_contract
)

router = APIRouter(prefix="/rendering", tags=["rendering"])


class ValidateExportRequest(BaseModel):
    version_number: int = 1
    format: str = "html"


@router.post("/{contract_id}/export")
def export(
    contract_id: int,
    payload: ExportRequest,
    session: Session = Depends(get_session),
):
    """Export a contract in the specified format."""
    result = export_contract(
        session, contract_id, payload.version_number, payload.format, payload
    )
    if result.status == "blocked":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Export blocked",
                "blockers": result.blockers,
                "warnings": result.warnings,
                "message": "Cannot export contract: blocker findings exist or required approval is missing"
            }
        )
    return result


@router.post("/{contract_id}/validate-export")
def validate_export_endpoint(
    contract_id: int,
    payload: ValidateExportRequest,
    session: Session = Depends(get_session),
):
    """Validate export eligibility for a contract."""
    return validate_export(session, contract_id, payload.version_number, payload.format)


@router.get("/{contract_id}/formats")
def available_formats(
    contract_id: int,
    session: Session = Depends(get_session),
):
    """Get available export formats for a contract."""
    validation = validate_export(session, contract_id, version_number=1, format="html")
    return {
        "formats": ["html", "docx", "pdf"] if validation["can_export"] else [],
        "blockers": validation.get("blockers", []),
        "status": validation.get("status", "blocked")
    }
