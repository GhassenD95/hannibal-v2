"""Two-pass generation engine.

Pass 1 -> ContractPlan; pass 2 -> per-section drafting. Content is drawn
exclusively from approved clauses + approved/effective sources; unsupported
sections abstain (needs_review/unsupported) and never fabricate.
"""

import re
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlmodel import Session, select

from apps.api.app.modules.core.models import (
    Contract, ContractSection, ContractRequest, ContractPlan,
    ContractVersion, Clause, LegalSource, PackVersion,
    SectionDefinition, Users, GenerationRun,
)
from apps.api.app.modules.core.audit import record_audit
from apps.api.app.modules.ai_providers.impl import MockLLMProvider
from apps.api.app.modules.contracts.service import (
    get_contract, get_sections, find_active_pack_and_type,
)
from apps.api.app.modules.rag.service import get_evidence_for_section

PLACEHOLDER_PATTERN = re.compile(r"(\[.*?\]|\{.*?\})")
PROMPT_VERSION = "1.0.0"
VALIDATION_VERSION = "1.0.0"


def _contract_facts(session: Session, contract: Contract) -> Dict[str, Any]:
    if contract.request_id is None:
        return {}
    request = session.get(ContractRequest, contract.request_id)
    return request.facts if request else {}


def _approved_clauses(session: Session, contract: Contract,
                      definition: SectionDefinition,
                      pack_version: PackVersion) -> List[Dict[str, Any]]:
    clauses = []
    statement = select(Clause).where(
        Clause.contract_type == contract.contract_type,
        Clause.status == "approved",
        Clause.pack_version_id == pack_version.id,
    )
    candidate_titles = (definition.default_clause_titles or []) + [definition.title]
    pool = list(session.exec(statement).all())
    for title in candidate_titles:
        match = next((c for c in pool if c.title.lower() == title.lower()), None)
        if match:
            clauses.append({"id": match.id, "title": match.title,
                            "content": match.content})
    return clauses


def _evidence_for_section(session: Session, contract: Contract,
                          section: ContractSection) -> List[Dict[str, Any]]:
    evidence = get_evidence_for_section(
        session, section.title, contract.jurisdiction, contract.contract_type, limit=5)
    return [e.model_dump(mode="json") for e in evidence]


def _sanitize_evidence(session: Session, evidence_ids: List[str]) -> List[str]:
    """Server-side re-check: only approved + effective sources pass."""
    out = []
    for value in evidence_ids:
        if not str(value).isdigit():
            continue
        source = session.get(LegalSource, int(value))
        if source is None or source.status != "approved":
            continue
        if source.effective_date and source.effective_date > datetime.utcnow():
            continue
        out.append(str(value))
    return out


def _match_definition(section_title: str,
                      definitions: List[SectionDefinition]) -> Optional[SectionDefinition]:
    """Deterministically map a contract section title to its section definition.

    Order: exact normalized title, exact normalized name, then token-prefix
    containment (e.g. 'disputes' name -> 'Dispute Resolution' title). Falls back
    to the first definition only when nothing matches.
    """
    def _norm(value: str) -> List[str]:
        return re.sub(r"[^a-z0-9]+", " ", value.lower()).split()

    section_tokens = _norm(section_title)
    for definition in definitions:
        if _norm(definition.title) == section_tokens:
            return definition
    for definition in definitions:
        if _norm(definition.name) == section_tokens:
            return definition

    best: Optional[SectionDefinition] = None
    best_score = 0
    for definition in definitions:
        score = 0
        for token in set(_norm(definition.name)) | set(_norm(definition.title)):
            if len(token) < 3:
                continue
            if any(len(t) >= 3 and (t.startswith(token) or token.startswith(t))
                   for t in section_tokens):
                score += 1
        if score > best_score:
            best, best_score = definition, score
    return best or (definitions[0] if definitions else None)


async def generate_section(
    session: Session, contract: Contract, section: ContractSection,
    definition: SectionDefinition, pack_version: PackVersion,
    provider=None,
) -> Tuple[ContractSection, GenerationRun]:
    provider = provider or MockLLMProvider()
    facts = _contract_facts(session, contract)
    clauses = _approved_clauses(session, contract, definition, pack_version)
    evidence = _evidence_for_section(session, contract, section)
    prompt_input = {
        "section_title": section.title,
        "contract_facts": facts,
        "approved_clauses": clauses,
        "retrieved_evidence": evidence,
        "is_required": definition.is_required,
    }
    output = await provider.generate_section(prompt_input)

    evidence_ids = _sanitize_evidence(session, output.get("evidence_ids", []))
    content = output.get("content", "") or ""
    status = output.get("status", "needs_review")
    if content and PLACEHOLDER_PATTERN.search(content):
        status = "needs_review"
    if not content.strip():
        status = "needs_review" if definition.is_required else "unsupported"
    allowed_clause_ids = {c["id"] for c in clauses}
    clause_ids = [int(cid) for cid in output.get("clause_ids", [])
                  if int(cid) in allowed_clause_ids] if all(
        str(cid).isdigit() for cid in output.get("clause_ids", [])) else []
    clause_ids = [cid for cid in clause_ids if cid in allowed_clause_ids]
    facts_used = list(set(output.get("facts_used", [])))

    section.content = content
    section.clause_ids = clause_ids
    section.evidence_ids = evidence_ids
    section.facts_used = facts_used
    section.status = status
    section.generated_at = datetime.utcnow()
    session.add(section)
    session.commit()
    session.refresh(section)

    run = GenerationRun(
        contract_id=contract.id,
        section_id=section.id,
        prompt_version=PROMPT_VERSION,
        model=provider.model_name,
        pack_version_id=pack_version.id,
        source_ids=evidence_ids,
        clause_ids=clause_ids,
        validation_version=VALIDATION_VERSION,
        input_snapshot={
            "section_title": section.title,
            "fact_keys": list(facts.keys()),
            "clause_titles": [c["title"] for c in clauses],
            "evidence_titles": [e.get("title", "") for e in evidence],
        },
        output_snapshot={
            "status": status,
            "abstain_reason": output.get("abstain_reason"),
            "character_count": len(content),
        },
        status=status,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return section, run


def build_plan(session: Session, user: Users, contract_id: int) -> ContractPlan:
    contract = get_contract(session, user, contract_id)
    result = find_active_pack_and_type(session, contract.contract_type,
                                       contract.jurisdiction)
    if result is None:
        raise ValueError("No active pack for this contract type; cannot plan")
    definitions = session.exec(select(SectionDefinition).where(
        SectionDefinition.contract_type_id == result["contract_type"].id
    ).order_by(SectionDefinition.order_index)).all()

    clauses = session.exec(select(Clause).where(
        Clause.pack_version_id == result["pack_version"].id,
        Clause.status == "approved",
        Clause.contract_type == contract.contract_type,
    )).all()

    evidence_ids: List[str] = []
    sections_db = session.exec(select(ContractSection).where(
        ContractSection.contract_id == contract.id)).all()
    for section in sections_db:
        for ev in _evidence_for_section(session, contract, section):
            sid = ev.get("source_id")
            if sid and sid not in evidence_ids:
                evidence_ids.append(str(sid))

    plan = session.exec(select(ContractPlan).where(
        ContractPlan.contract_id == contract_id).order_by(
        ContractPlan.id.desc())).first()
    if plan is None:
        plan = ContractPlan(contract_id=contract_id)
        session.add(plan)
    plan.title = f"Plan for {contract.name}"
    plan.sections_required = [d.name for d in definitions if d.is_required]
    plan.sections_complete = [d.name for d in definitions]
    plan.selected_clauses = [c.id for c in clauses]
    plan.evidence_ids = evidence_ids
    plan.unresolved_decisions = []
    plan.status = "pending"
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return plan


async def generate_contract(session: Session, user: Users,
                            contract_id: int) -> Dict[str, Any]:
    contract = get_contract(session, user, contract_id)
    result = find_active_pack_and_type(session, contract.contract_type,
                                       contract.jurisdiction)
    if result is None:
        raise ValueError("No active pack for this contract type; cannot generate")
    definitions = session.exec(select(SectionDefinition).where(
        SectionDefinition.contract_type_id == result["contract_type"].id
    ).order_by(SectionDefinition.order_index)).all()
    sections = session.exec(select(ContractSection).where(
        ContractSection.contract_id == contract.id).order_by(
        ContractSection.order_index)).all()

    counts = {"supported": 0, "needs_review": 0, "unsupported": 0}
    definitions_list = list(definitions)
    for section in sections:
        definition = _match_definition(section.title, definitions_list)
        await generate_section(session, contract, section, definition,
                               result["pack_version"])
        counts[section.status] = counts.get(section.status, 0) + 1

    contract.status = "drafted"
    session.add(contract)
    session.commit()
    record_audit(session, "generation", user_id=user.id, contract_id=contract.id,
                 generated_sections=len(sections), **counts)
    return {
        "contract_id": contract.id,
        "status": "drafted",
        "generated_sections": len(sections),
        **counts,
    }


async def regenerate_section(session: Session, user: Users, contract_id: int,
                             section_id: int) -> Tuple[ContractSection, int]:
    contract = get_contract(session, user, contract_id)
    result = find_active_pack_and_type(session, contract.contract_type,
                                       contract.jurisdiction)
    if result is None:
        raise ValueError("No active pack for this contract type")
    section = session.get(ContractSection, section_id)
    if section is None or section.contract_id != contract_id:
        raise ValueError("Section not found")
    definitions = session.exec(select(SectionDefinition).where(
        SectionDefinition.contract_type_id == result["contract_type"].id)).all()
    definition = _match_definition(section.title, list(definitions))
    section, run = await generate_section(session, contract, section, definition,
                                          result["pack_version"])

    max_version = session.exec(select(ContractVersion).where(
        ContractVersion.contract_id == contract_id).order_by(
        ContractVersion.version_number.desc())).first()
    version_number = (max_version.version_number + 1) if max_version else 1
    new_version = ContractVersion(
        contract_id=contract_id,
        version_number=version_number,
        title=contract.name,
        content=json.dumps(
            {
                s.title: s.content
                for s in session.exec(select(ContractSection).where(
                    ContractSection.contract_id == contract_id).order_by(
                    ContractSection.order_index)).all()
            },
            ensure_ascii=False,
        ),
        is_active=True,
    )
    session.add(new_version)
    if max_version:
        max_version.is_active = False
        session.add(max_version)
    session.commit()
    session.refresh(new_version)
    record_audit(session, "section_regenerated", user_id=user.id,
                 contract_id=contract_id, section_id=section.id,
                 version_number=version_number)
    return section, version_number