from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from apps.api.app.modules.core.db import get_session
from apps.api.app.modules.core.models import Users, AuditEvent, ContractVersion
from apps.api.app.modules.auth.deps import get_current_user
from apps.api.app.modules.contracts import service
from apps.api.app.modules.contracts.schemas import (
    ContractRequestCreate, InterpretRequest, ContractUpdate,
    SectionCreate, SectionUpdate,
)

router = APIRouter(prefix="/contracts", tags=["contracts"])


class ApproveRequest(BaseModel):
    notes: str | None = None


class ExportRequest(BaseModel):
    format: str  # html, docx, pdf


def _to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, service.OrgPermissionError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, service.NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


@router.post("")
def create_request(
    payload: ContractRequestCreate,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    try:
        request = service.create_contract_request(session, user, payload.model_dump())
    except Exception as exc:  # noqa: BLE001
        raise _to_http(exc) from exc
    return {
        "kind": "request",
        "id": request.id,
        "name": request.name,
        "contract_type": request.contract_type,
        "jurisdiction": request.jurisdiction,
        "facts": request.facts,
        "status": request.status,
    }


@router.post("/{request_id}/interpret")
def interpret(
    request_id: int,
    payload: InterpretRequest,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    try:
        request = service.interpret_request(session, user, request_id,
                                            payload.description)
    except Exception as exc:  # noqa: BLE001
        raise _to_http(exc) from exc
    return {"kind": "request", "id": request.id,
            "contract_type": request.contract_type,
            "jurisdiction": request.jurisdiction,
            "facts": request.facts,
            "status": request.status}


@router.post("/{request_id}/confirm-request")
def confirm_request_endpoint(
    request_id: int,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    try:
        contract = service.confirm_request(session, user, request_id)
    except Exception as exc:  # noqa: BLE001
        raise _to_http(exc) from exc
    sections = service.get_sections(session, user, contract.id)
    return {
        "kind": "contract",
        "id": contract.id,
        "name": contract.name,
        "contract_type": contract.contract_type,
        "jurisdiction": contract.jurisdiction,
        "status": contract.status,
        "section_count": len(sections),
        "sections": [
            {"id": s.id, "title": s.title, "order_index": s.order_index,
             "status": s.status}
            for s in sections
        ],
    }


@router.get("")
def list_contracts_endpoint(
    contract_type: str = None,
    jurisdiction: str = None,
    status: str = None,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    contracts = service.list_contracts(session, user, contract_type, jurisdiction,
                                       status)
    return [
        {"id": c.id, "name": c.name, "contract_type": c.contract_type,
         "jurisdiction": c.jurisdiction, "status": c.status,
         "updated_at": str(c.updated_at) if c.updated_at else None}
        for c in contracts
    ]


@router.get("/{contract_id}")
def get_contract_endpoint(
    contract_id: int,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    try:
        contract = service.get_contract(session, user, contract_id)
    except Exception as exc:  # noqa: BLE001
        raise _to_http(exc) from exc
    return {
        "kind": "contract",
        "id": contract.id,
        "name": contract.name,
        "description": contract.description,
        "contract_type": contract.contract_type,
        "jurisdiction": contract.jurisdiction,
        "language": contract.language,
        "status": contract.status,
        "request_id": contract.request_id,
    }


@router.patch("/{contract_id}")
def update_contract_endpoint(
    contract_id: int,
    payload: ContractUpdate,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    try:
        contract = service.update_contract(session, user, contract_id,
                                           payload.model_dump(exclude_unset=True))
    except Exception as exc:  # noqa: BLE001
        raise _to_http(exc) from exc
    return {"id": contract.id, "name": contract.name, "status": contract.status}


@router.get("/{contract_id}/sections")
def list_sections_endpoint(
    contract_id: int,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    try:
        sections = service.get_sections(session, user, contract_id)
    except Exception as exc:  # noqa: BLE001
        raise _to_http(exc) from exc
    return [
        {"id": s.id, "title": s.title, "content": s.content,
         "order_index": s.order_index, "status": s.status,
         "clause_ids": s.clause_ids, "evidence_ids": s.evidence_ids,
         "facts_used": s.facts_used}
        for s in sections
    ]


@router.post("/{contract_id}/sections")
def create_section_endpoint(
    contract_id: int,
    payload: SectionCreate,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    try:
        section = service.create_section(session, user, contract_id,
                                         payload.title, payload.order_index)
    except Exception as exc:  # noqa: BLE001
        raise _to_http(exc) from exc
    return {"id": section.id, "title": section.title, "status": section.status}


@router.patch("/{contract_id}/sections/{section_id}")
def update_section_endpoint(
    contract_id: int,
    section_id: int,
    payload: SectionUpdate,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    try:
        section = service.update_section(session, user, contract_id, section_id,
                                         payload.model_dump(exclude_unset=True))
    except Exception as exc:  # noqa: BLE001
        raise _to_http(exc) from exc
    return {"id": section.id, "title": section.title, "status": section.status}


@router.get("/{contract_id}/sections/{section_id}/evidence")
def section_evidence_endpoint(
    contract_id: int,
    section_id: int,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    try:
        evidence = service.section_evidence(session, user, contract_id, section_id)
    except Exception as exc:  # noqa: BLE001
        raise _to_http(exc) from exc
    return {"section_id": section_id, "evidence": evidence}


@router.get("/{contract_id}/sections/{section_id}/risks")
def section_risks_endpoint(
    contract_id: int,
    section_id: int,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    try:
        service.get_section(session, user, contract_id, section_id)
    except Exception as exc:  # noqa: BLE001
        raise _to_http(exc) from exc
    from apps.api.app.modules.core.models import RiskFinding
    risks = list(session.exec(
        select(RiskFinding).where(
            (RiskFinding.contract_id == contract_id) &
            (RiskFinding.section_id == section_id))
    ).all())
    return {"section_id": section_id,
            "risks": [
                {"id": r.id, "title": r.title, "severity": r.severity,
                 "explanation": r.explanation, "status": r.status}
                for r in risks
            ]}


@router.post("/{contract_id}/plan")
def plan_contract(
    contract_id: int,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    from apps.api.app.modules.generation.service import build_plan
    try:
        plan = build_plan(session, user, contract_id)
    except Exception as exc:  # noqa: BLE001
        raise _to_http(exc) from exc
    return {
        "id": plan.id,
        "contract_id": contract_id,
        "sections_required": plan.sections_required,
        "sections_complete": plan.sections_complete,
        "selected_clauses": plan.selected_clauses,
        "evidence_ids": plan.evidence_ids,
        "unresolved_decisions": plan.unresolved_decisions,
        "status": plan.status,
    }


@router.post("/{contract_id}/generate")
async def generate_contract_endpoint(
    contract_id: int,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    from apps.api.app.modules.generation.service import generate_contract
    try:
        result = await generate_contract(session, user, contract_id)
    except Exception as exc:  # noqa: BLE001
        raise _to_http(exc) from exc
    return result


@router.post("/{contract_id}/sections/{section_id}/regenerate")
async def regenerate_section_endpoint(
    contract_id: int,
    section_id: int,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    from apps.api.app.modules.generation.service import regenerate_section
    try:
        section, version_number = await regenerate_section(
            session, user, contract_id, section_id)
    except Exception as exc:  # noqa: BLE001
        raise _to_http(exc) from exc
    return {
        "section_id": section.id,
        "title": section.title,
        "status": section.status,
        "content": section.content,
        "clause_ids": section.clause_ids,
        "evidence_ids": section.evidence_ids,
        "facts_used": section.facts_used,
        "new_version_number": version_number,
    }


@router.post("/{contract_id}/validate")
def validate_contract_endpoint(
    contract_id: int,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    from apps.api.app.modules.validation.service import run_validation
    from apps.api.app.modules.core.audit import record_audit
    try:
        service.get_contract(session, user, contract_id)
    except Exception as exc:  # noqa: BLE001
        raise _to_http(exc) from exc
    result = run_validation(session, contract_id, run_by=user.id)
    contract = service.get_contract(session, user, contract_id)
    contract.status = "needs_review" if result["blockers"] else "validated"
    session.add(contract)
    if not result["blockers"]:
        active_version = session.exec(select(ContractVersion).where(
            ContractVersion.contract_id == contract_id,
            ContractVersion.is_active == True,
        )).first()
        if active_version:
            active_version.validated = True
            session.add(active_version)
    session.commit()
    record_audit(session, "validation", user_id=user.id, contract_id=contract_id,
                 blockers=result["blockers"])
    return result


@router.get("/{contract_id}/validation/summary")
def validation_summary_endpoint(
    contract_id: int,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    from apps.api.app.modules.validation.service import open_blockers, DETERMINISTIC_RULES
    from apps.api.app.modules.core.models import ValidationFinding
    try:
        service.get_contract(session, user, contract_id)
    except Exception as exc:  # noqa: BLE001
        raise _to_http(exc) from exc
    findings = session.exec(select(ValidationFinding).where(
        ValidationFinding.contract_id == contract_id,
        ValidationFinding.status == "open")).all()
    blockers = sum(1 for f in findings if f.severity == "blocker")
    high_risks = sum(1 for f in findings if f.severity == "high")
    warnings = sum(1 for f in findings if f.severity == "warning")
    return {
        "status": "needs_review" if blockers else "valid",
        "blockers": blockers,
        "high_risks": high_risks,
        "warnings": warnings,
        "passed_checks": max(0, len(DETERMINISTIC_RULES) - (blockers + high_risks)),
        "total_checks": len(DETERMINISTIC_RULES),
    }


@router.post("/{contract_id}/risk")
async def risk_analysis_endpoint(
    contract_id: int,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    from apps.api.app.modules.risks.service import run_risk_analysis
    try:
        result = await run_risk_analysis(session, user, contract_id)
    except Exception as exc:  # noqa: BLE001
        raise _to_http(exc) from exc
    return result


@router.get("/{contract_id}/risks")
def list_risks_endpoint(
    contract_id: int,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    from apps.api.app.modules.core.models import RiskFinding
    try:
        service.get_contract(session, user, contract_id)
    except Exception as exc:  # noqa: BLE001
        raise _to_http(exc) from exc
    risks = session.exec(select(RiskFinding).where(
        RiskFinding.contract_id == contract_id).order_by(RiskFinding.id)).all()
    return [
        {"id": r.id, "title": r.title, "severity": r.severity,
         "explanation": r.explanation, "location": r.location,
         "recommendation": r.recommendation, "status": r.status,
         "section_id": r.section_id}
        for r in risks
    ]


@router.post("/{contract_id}/approve")
def approve_contract_endpoint(
    contract_id: int,
    payload: ApproveRequest = ApproveRequest(),
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    from apps.api.app.modules.approvals.service import (
        approve_contract, ApprovalError,
    )
    try:
        result = approve_contract(session, user, contract_id, payload.notes)
    except ApprovalError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise _to_http(exc) from exc
    return result


@router.get("/{contract_id}/approvals")
def list_approvals_endpoint(
    contract_id: int,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    from apps.api.app.modules.approvals.service import list_approvals
    try:
        return list_approvals(session, user, contract_id)
    except Exception as exc:  # noqa: BLE001
        raise _to_http(exc) from exc


@router.get("/{contract_id}/versions")
def list_versions_endpoint(
    contract_id: int,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    from apps.api.app.modules.core.models import ContractVersion
    try:
        service.get_contract(session, user, contract_id)
    except Exception as exc:  # noqa: BLE001
        raise _to_http(exc) from exc
    versions = list(session.exec(select(ContractVersion).where(
        ContractVersion.contract_id == contract_id).order_by(
        ContractVersion.version_number)).all())
    return [
        {"version_number": v.version_number, "title": v.title,
         "is_active": v.is_active, "validated": v.validated,
         "approved": v.approved, "created_at": v.created_at.isoformat()}
        for v in versions
    ]


@router.get("/{contract_id}/audit")
def list_audit_events_endpoint(
    contract_id: int,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    try:
        service.get_contract(session, user, contract_id)
    except Exception as exc:  # noqa: BLE001
        raise _to_http(exc) from exc
    events = list(session.exec(select(AuditEvent).where(
        AuditEvent.contract_id == contract_id).order_by(
        AuditEvent.id.desc())).all())
    return [
        {"id": e.id, "event_type": e.event_type, "event_data": e.event_data,
         "user_id": e.user_id, "created_at": e.created_at.isoformat()}
        for e in events
    ]


@router.post("/{contract_id}/export")
def export_contract_endpoint(
    contract_id: int,
    payload: ExportRequest,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    from apps.api.app.modules.rendering.service import (
        final_export, ExportBlockedError,
    )
    try:
        return final_export(session, user, contract_id, payload.format)
    except ExportBlockedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise _to_http(exc) from exc


@router.get("/{contract_id}/export/{export_id}/content")
def export_content_endpoint(
    contract_id: int,
    export_id: int,
    session: Session = Depends(get_session),
    user: Users = Depends(get_current_user),
):
    from fastapi.responses import Response
    from apps.api.app.modules.core.models import ExportFile
    from apps.api.app.modules.rendering.service import (
        read_export_content, ExportNotFoundError, _export_media_type,
    )
    try:
        content = read_export_content(session, user, contract_id, export_id)
    except ExportNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise _to_http(exc) from exc
    export_file = session.get(ExportFile, export_id)
    return Response(
        content=content,
        media_type=_export_media_type(export_file.format if export_file else ""),
    )