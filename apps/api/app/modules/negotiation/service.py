"""Negotiation business logic: create, analyze, propose, decide (audited)."""

import json
from typing import Any, Dict, List

from sqlmodel import Session, select

from apps.api.app.modules.core.models import Users, NegotiationItem
from apps.api.app.modules.core.audit import record_audit
from apps.api.app.modules.ai_providers.impl import MockLLMProvider
from apps.api.app.modules.contracts.service import get_contract, get_section, \
    update_section


class NegotiationError(Exception):
    pass


def list_negotiations(session: Session, user: Users,
                      contract_id: int) -> List[Dict[str, Any]]:
    get_contract(session, user, contract_id)
    items = list(session.exec(select(NegotiationItem).where(
        NegotiationItem.contract_id == contract_id).order_by(
        NegotiationItem.id)).all())
    return [
        {
            "id": item.id,
            "contract_id": item.contract_id,
            "section_id": item.section_id,
            "original_clause_id": item.original_clause_id,
            "counterparty_clause": item.counterparty_clause,
            "hannibal_analysis": item.hannibal_analysis,
            "proposed_text": item.proposed_text,
            "status": item.status,
        }
        for item in items
    ]


def create_negotiation(session: Session, user: Users, contract_id: int,
                       section_id: int, counterparty_clause: str,
                       original_clause_id: int | None = None) -> Dict[str, Any]:
    get_contract(session, user, contract_id)
    get_section(session, user, contract_id, section_id)
    item = NegotiationItem(
        contract_id=contract_id,
        section_id=section_id,
        original_clause_id=original_clause_id,
        counterparty_clause=counterparty_clause,
        status="pending",
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    record_audit(session, "negotiation_created", user_id=user.id,
                 contract_id=contract_id, item_id=item.id)
    return _serialize(item)


def _get_item(session: Session, user: Users, contract_id: int,
              item_id: int) -> NegotiationItem:
    get_contract(session, user, contract_id)
    item = session.get(NegotiationItem, item_id)
    if item is None or item.contract_id != contract_id:
        raise NegotiationError("Negotiation item not found")
    return item


def _serialize(item: NegotiationItem) -> Dict[str, Any]:
    return {
        "id": item.id,
        "contract_id": item.contract_id,
        "section_id": item.section_id,
        "original_clause_id": item.original_clause_id,
        "counterparty_clause": item.counterparty_clause,
        "hannibal_analysis": item.hannibal_analysis,
        "proposed_text": item.proposed_text,
        "status": item.status,
    }


async def analyze_negotiation(session: Session, user: Users, contract_id: int,
                              item_id: int) -> Dict[str, Any]:
    item = _get_item(session, user, contract_id, item_id)
    section = None
    if item.section_id:
        section = get_section(session, user, contract_id, item.section_id)
    provider = MockLLMProvider()
    analysis = await provider.analyze_negotiation({
        "baseline_clause": section.content if section else "Standard clause",
        "counterparty_clause": item.counterparty_clause or "",
    })
    item.hannibal_analysis = json.dumps({
        "deviations": analysis.get("deviations", []),
        "risk_assessment": analysis.get("risk_assessment", "low"),
        "recommendation": analysis.get("recommendation", ""),
        "requires_human_decision": analysis.get("requires_human_decision", False),
    }, ensure_ascii=False)
    session.add(item)
    session.commit()
    session.refresh(item)
    record_audit(session, "negotiation_analyzed", user_id=user.id,
                 contract_id=contract_id, item_id=item.id)
    return _serialize(item)


async def propose_negotiation(session: Session, user: Users, contract_id: int,
                              item_id: int) -> Dict[str, Any]:
    item = _get_item(session, user, contract_id, item_id)
    if item.hannibal_analysis is None:
        await analyze_negotiation(session, user, contract_id, item_id)
        session.refresh(item)
    section = None
    if item.section_id:
        section = get_section(session, user, contract_id, item.section_id)
    baseline = section.content if section else (item.counterparty_clause or "")
    item.proposed_text = (
        baseline
        + "\n\n[Amended by negotiation] "
        + "Proposed replacement wording based on Hannibal analysis."
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    record_audit(session, "negotiation_proposed", user_id=user.id,
                 contract_id=contract_id, item_id=item.id)
    return _serialize(item)


def decide_negotiation(session: Session, user: Users, contract_id: int,
                       item_id: int, decision: str) -> Dict[str, Any]:
    if decision not in ("accepted", "rejected", "escalated"):
        raise NegotiationError(
            "Decision must be one of: accepted, rejected, escalated")
    item = _get_item(session, user, contract_id, item_id)
    item.status = decision
    session.add(item)
    session.commit()
    session.refresh(item)
    if decision == "accepted" and item.section_id and item.proposed_text:
        # Apply the negotiated wording and create an immutable snapshot
        update_section(session, user, contract_id, item.section_id,
                       {"content": item.proposed_text, "status": "needs_review"})
    record_audit(session, "negotiation_decided", user_id=user.id,
                 contract_id=contract_id, item_id=item.id, decision=decision)
    session.refresh(item)
    return _serialize(item)