"""Contract lifecycle business logic (org-scoped, audited)."""

import json
import re
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from datetime import datetime

from apps.api.app.modules.core.models import (
    ContractRequest, Contract, ContractSection, ContractVersion,
    JurisdictionPack, PackVersion, ContractType, SectionDefinition,
    Users,
)
from apps.api.app.modules.core.audit import record_audit
from apps.api.app.modules.rag.service import get_evidence_for_section
from apps.api.app.modules.information_collector.service import (
    normalize_contract_type, normalize_jurisdiction,
)


class OrgPermissionError(Exception):
    pass


class NotFoundError(Exception):
    pass


def _ensure_org_access(user: Users, organization_id: Optional[int]) -> None:
    """Superusers see all orgs; normal users only their own."""
    if user.is_superuser:
        return
    if organization_id != user.organization_id:
        raise OrgPermissionError("Cross-organization access denied")


def create_contract_request(
    session: Session, user: Users, payload: Dict[str, Any]
) -> ContractRequest:
    request = ContractRequest(
        name=payload["name"],
        description=payload.get("description"),
        contract_type=normalize_contract_type(payload["contract_type"]),
        jurisdiction=normalize_jurisdiction(payload.get("jurisdiction", "MA")),
        language=payload.get("language", "fr"),
        status="draft",
        facts=payload.get("facts") or {},
        selected_clauses=payload.get("selected_clauses") or [],
        evidence_ids=payload.get("evidence_ids") or [],
        organization_id=user.organization_id,
    )
    session.add(request)
    session.commit()
    session.refresh(request)
    record_audit(session, "request_created", user_id=user.id,
                 contract_id=None, request_id=request.id,
                 contract_type=request.contract_type)
    return request


def get_contract_request(session: Session, user: Users,
                         request_id: int) -> ContractRequest:
    request = session.get(ContractRequest, request_id)
    if request is None:
        raise NotFoundError("Contract request not found")
    _ensure_org_access(user, request.organization_id)
    return request


def extract_facts_from_description(description: str) -> Dict[str, str]:
    """Deterministic lightweight extraction (no legal drafting)."""
    desc_lower = description.lower()
    facts: Dict[str, str] = {}
    duration_match = re.search(r'(\d+)\s*-?\s*(month|months|year|years|an|ans)', desc_lower)
    if duration_match:
        unit_word = duration_match.group(2)
        unit = "years" if unit_word.startswith("year") or unit_word.startswith("an") else "months"
        facts["duration"] = f"{duration_match.group(1)} {unit}"
    amount_match = re.search(r'(\d[\d\s.,]*)\s*(?:mad|dh|dollar|dhs|tnd|dt|dinar|€|\$)', desc_lower)
    if amount_match:
        facts["amount"] = amount_match.group(1).strip()
    party_match = re.search(r'(?:between|for)\s+([A-Z][A-Za-z0-9\s.-]+?)\s+(?:and|against|per|,|$)', description)
    if party_match:
        facts["parties"] = party_match.group(1).strip()
    if "nda" in desc_lower or "non-disclosure" in desc_lower:
        purpose_match = re.search(r'purpose of (?:the disclosure|this)?\s*:?\s*([^.]*)', desc_lower)
        if purpose_match and purpose_match.group(1).strip():
            facts["purpose"] = purpose_match.group(1).strip()
    return facts


def interpret_request(session: Session, user: Users, request_id: int,
                      description: str) -> ContractRequest:
    request = get_contract_request(session, user, request_id)
    desc_lower = description.lower()
    if "nda" in desc_lower or "non-disclosure" in desc_lower:
        request.contract_type = normalize_contract_type("nda")
    elif "service" in desc_lower or "agreement" in desc_lower:
        request.contract_type = normalize_contract_type("service_agreement")
    if "maroc" in desc_lower or "morocco" in desc_lower:
        request.jurisdiction = "MA"
    if "tunisie" in desc_lower or "tunisia" in desc_lower:
        request.jurisdiction = "TN"
    request.facts = {**request.facts, **extract_facts_from_description(description)}
    request.description = description
    request.status = "interpreted"
    session.add(request)
    session.commit()
    session.refresh(request)
    record_audit(session, "request_interpreted", user_id=user.id,
                 request_id=request.id, contract_type=request.contract_type)
    return request


def find_active_pack_and_type(session: Session, contract_type: str,
                              jurisdiction: str) -> Optional[Dict[str, Any]]:
    """Find an active pack for a jurisdiction that declares the contract type.

    Packs store their jurisdiction and declared contract types in pack
    metadata, so packs for different jurisdictions can coexist. Falls back to
    the legacy ContractType.pack_version_id join for previously seeded data.
    """
    statement = (
        select(JurisdictionPack, PackVersion)
        .join(PackVersion, PackVersion.pack_id == JurisdictionPack.id)
        .where(JurisdictionPack.status == "active")
        .where(PackVersion.status == "active")
        .order_by(PackVersion.id.desc())
    )
    for pack, pack_version in session.exec(statement).all():
        meta = pack.pack_metadata or {}
        if meta.get("jurisdiction") != jurisdiction:
            continue
        declared = [s.strip() for s in (meta.get("contract_types") or "").split(",")
                    if s.strip()]
        if contract_type not in declared:
            continue
        contract_definition = session.exec(
            select(ContractType).where(ContractType.name == contract_type)
        ).first()
        if contract_definition is None:
            continue
        return {
            "pack": pack,
            "pack_version": pack_version,
            "contract_type": contract_definition,
        }

    legacy_statement = (
        select(ContractType, PackVersion, JurisdictionPack)
        .join(PackVersion, PackVersion.id == ContractType.pack_version_id)
        .join(JurisdictionPack, JurisdictionPack.id == PackVersion.pack_id)
        .where(ContractType.name == contract_type)
        .where(PackVersion.status == "active")
        .where(JurisdictionPack.status == "active")
    )
    row = session.exec(legacy_statement).first()
    if row is None:
        return None
    contract_definition, pack_version, pack = row
    return {
        "pack": pack,
        "pack_version": pack_version,
        "contract_type": contract_definition,
    }


def confirm_request(session: Session, user: Users, request_id: int) -> Contract:
    request = get_contract_request(session, user, request_id)
    result = find_active_pack_and_type(session, request.contract_type,
                                       request.jurisdiction)
    if result is None:
        raise ValueError(
            "No active pack supports this contract type/jurisdiction; cannot confirm")
    contract = Contract(
        name=request.name,
        description=request.description,
        contract_type=request.contract_type,
        jurisdiction=request.jurisdiction,
        language=request.language,
        status="requested",
        request_id=request.id,
        organization_id=user.organization_id,
    )
    session.add(contract)
    session.commit()
    session.refresh(contract)

    definitions = session.exec(select(SectionDefinition).where(
        SectionDefinition.contract_type_id == result["contract_type"].id
    ).order_by(SectionDefinition.order_index)).all()
    for definition in definitions:
        session.add(ContractSection(
            contract_id=contract.id,
            title=definition.title,
            content="",
            order_index=definition.order_index,
            clause_ids=[],
            evidence_ids=[],
            status="pending",
        ))
    session.commit()

    request.status = "confirmed"
    session.add(request)
    session.commit()
    record_audit(session, "contract_confirmed", user_id=user.id,
                 contract_id=contract.id, contract_type=contract.contract_type)
    return contract


def list_contracts(session: Session, user: Users,
                   contract_type: Optional[str] = None,
                   jurisdiction: Optional[str] = None,
                   status: Optional[str] = None) -> List[Contract]:
    statement = select(Contract)
    if not user.is_superuser:
        statement = statement.where(Contract.organization_id == user.organization_id)
    if contract_type:
        statement = statement.where(Contract.contract_type == contract_type)
    if jurisdiction:
        statement = statement.where(Contract.jurisdiction == jurisdiction)
    if status:
        statement = statement.where(Contract.status == status)
    return list(session.exec(statement.order_by(Contract.id.desc())).all())  # pylint: disable=no-member


def get_contract(session: Session, user: Users, contract_id: int) -> Contract:
    contract = session.get(Contract, contract_id)
    if contract is None:
        raise NotFoundError("Contract not found")
    _ensure_org_access(user, contract.organization_id)
    return contract


def update_contract(session: Session, user: Users, contract_id: int,
                    payload: Dict[str, Any]) -> Contract:
    contract = get_contract(session, user, contract_id)
    if payload.get("name") is not None:
        contract.name = payload["name"]
    if payload.get("description") is not None:
        contract.description = payload["description"]
    contract.updated_at = datetime.utcnow()
    session.add(contract)
    session.commit()
    session.refresh(contract)
    record_audit(session, "contract_updated", user_id=user.id, contract_id=contract.id)
    return contract


def get_sections(session: Session, user: Users, contract_id: int) -> List[ContractSection]:
    get_contract(session, user, contract_id)
    return list(session.exec(select(ContractSection).where(
        ContractSection.contract_id == contract_id
    ).order_by(ContractSection.order_index)).all())


def create_section(session: Session, user: Users, contract_id: int,
                   title: str, order_index: int) -> ContractSection:
    get_contract(session, user, contract_id)
    section = ContractSection(
        contract_id=contract_id, title=title, content="",
        order_index=order_index, status="pending",
    )
    session.add(section)
    session.commit()
    session.refresh(section)
    return section


def get_section(session: Session, user: Users, contract_id: int,
                section_id: int) -> ContractSection:
    get_contract(session, user, contract_id)
    section = session.get(ContractSection, section_id)
    if section is None or section.contract_id != contract_id:
        raise NotFoundError("Section not found")
    return section


def update_section(session: Session, user: Users, contract_id: int,
                   section_id: int, payload: Dict[str, Any]) -> ContractSection:
    get_contract(session, user, contract_id)
    section = session.get(ContractSection, section_id)
    if section is None or section.contract_id != contract_id:
        raise NotFoundError("Section not found")
    if payload.get("content") is not None and section.content != payload["content"]:
        # Immutable draft history: snapshot the current state before editing
        snapshot_contract_version(session, contract_id)
    for field in ("content", "title", "status", "clause_ids", "evidence_ids",
                  "facts_used"):
        if payload.get(field) is not None:
            setattr(section, field, payload[field])
    session.add(section)
    session.commit()
    session.refresh(section)
    record_audit(session, "section_updated", user_id=user.id, contract_id=contract_id,
                 section_id=section.id)
    return section


def section_evidence(session: Session, user: Users, contract_id: int,
                     section_id: int) -> List[Dict[str, Any]]:
    contract = get_contract(session, user, contract_id)
    section = get_section(session, user, contract_id, section_id)
    return get_evidence_for_section(
        session, section.title, contract.jurisdiction, contract.contract_type
    )


def _snapshot_content(session: Session, contract_id: int) -> str:
    sections = list(session.exec(select(ContractSection).where(
        ContractSection.contract_id == contract_id).order_by(
        ContractSection.order_index)).all())
    return json.dumps(
        {
            s.title: {
                "content": s.content,
                "status": s.status,
                "clause_ids": s.clause_ids,
                "evidence_ids": s.evidence_ids,
                "facts_used": s.facts_used,
            }
            for s in sections
        },
        ensure_ascii=False,
    )


def snapshot_contract_version(session: Session, contract_id: int) -> ContractVersion:
    """Create an immutable snapshot of the current contract state."""
    contract = session.get(Contract, contract_id)
    if contract is None:
        raise NotFoundError("Contract not found")
    return create_contract_version(
        session, contract_id, contract.name,
        _snapshot_content(session, contract_id),
    )


def create_contract_version(session: Session, contract_id: int,
                            title: str, content: str) -> ContractVersion:
    max_version = session.exec(select(ContractVersion).where(
        ContractVersion.contract_id == contract_id).order_by(
        ContractVersion.version_number.desc())).first()
    version_number = (max_version.version_number + 1) if max_version else 1
    version = ContractVersion(
        contract_id=contract_id,
        version_number=version_number,
        title=title,
        content=content,
        is_active=True,
    )
    session.add(version)
    if max_version:
        max_version.is_active = False
        session.add(max_version)
    session.commit()
    session.refresh(version)
    return version