from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Session, select

from apps.api.app.modules.core.models import (
    Users, Approval, ContractVersion, ValidationFinding,
)
from apps.api.app.modules.core.audit import record_audit
from apps.api.app.modules.contracts.service import get_contract, \
    NotFoundError, OrgPermissionError


class ApprovalError(Exception):
    pass


def _latest_version(session: Session, contract_id: int) -> ContractVersion | None:
    return session.exec(select(ContractVersion).where(
        ContractVersion.contract_id == contract_id).order_by(
        ContractVersion.version_number.desc())).first()


def open_blocker_findings(session: Session, contract_id: int) -> List:
    return list(session.exec(select(ValidationFinding).where(
        ValidationFinding.contract_id == contract_id,
        ValidationFinding.severity == "blocker",
        ValidationFinding.status == "open")).all())


def approve_contract(session: Session, user: Users, contract_id: int,
                     notes: str | None = None) -> Dict[str, Any]:
    """Approve a contract when zero open blockers exist. Creates an approval
    record, marks the latest version approved, and sets contract status."""
    contract = get_contract(session, user, contract_id)
    blockers = open_blocker_findings(session, contract_id)
    if blockers:
        raise ApprovalError(
            f"Approval blocked: {len(blockers)} open blocker finding(s) must "
            f"be resolved first")

    latest = _latest_version(session, contract_id)
    approval = Approval(
        contract_id=contract_id,
        version_id=latest.id if latest else None,
        approver_id=user.id,
        approval_type="human",
        notes=notes,
        approved_at=datetime.utcnow(),
    )
    session.add(approval)
    if latest:
        latest.is_active = True
        latest.approved = True
        session.add(latest)
    contract.status = "approved"
    contract.updated_at = datetime.utcnow()
    session.add(contract)
    session.commit()
    session.refresh(approval)

    record_audit(session, "contract_approved", user_id=user.id,
                 contract_id=contract_id, approval_id=approval.id)
    return {
        "approval_id": approval.id,
        "contract_id": contract_id,
        "version_id": latest.id if latest else None,
        "approver_id": user.id,
        "approval_type": "human",
        "approved_at": approval.approved_at.isoformat(),  # pylint: disable=no-member
    }


def list_approvals(session: Session, user: Users,
                   contract_id: int) -> List[Dict[str, Any]]:
    get_contract(session, user, contract_id)
    approvals = session.exec(select(Approval).where(
        Approval.contract_id == contract_id).order_by(Approval.id)).all()
    return [
        {
            "id": a.id,
            "contract_id": a.contract_id,
            "version_id": a.version_id,
            "approver_id": a.approver_id,
            "approval_type": a.approval_type,
            "notes": a.notes,
            "approved_at": a.approved_at.isoformat(),
        }
        for a in approvals
    ]