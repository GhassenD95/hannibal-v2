"""Risk analysis: deterministic from validation findings + mock qualitative review."""

from typing import Any, Dict, List

from sqlmodel import Session, select

from apps.api.app.modules.core.models import (
    Users, Contract, ContractSection, RiskFinding, ValidationRun,
)
from apps.api.app.modules.core.audit import record_audit
from apps.api.app.modules.ai_providers.impl import MockLLMProvider
from apps.api.app.modules.contracts.service import get_contract
from apps.api.app.modules.validation.service import open_blockers

PLAYBOOK_MARKERS = {
    "placeholder": "Unresolved placeholder indicates an incomplete section",
    "currency": "Currency mismatch between facts and the payment section",
    "governing law": "Missing or weak governing law for a Moroccan contract",
    "liability": "Liability cap absent or exposure excessive",
    "termination": "Termination notice below market standard",
}


async def run_risk_analysis(session: Session, user: Users,
                            contract_id: int) -> Dict[str, Any]:
    contract = get_contract(session, user, contract_id)
    findings = open_blockers(session, contract_id)
    sections = list(session.exec(select(ContractSection).where(
        ContractSection.contract_id == contract_id).order_by(
        ContractSection.order_index)).all())

    risks: List[RiskFinding] = []
    for section in sections:
        # Deterministic findings from content markers
        section_lower = section.title.lower() + " " + section.content.lower()
        for marker, message in PLAYBOOK_MARKERS.items():
            if marker in section_lower:
                risks.append(RiskFinding(
                    contract_id=contract_id,
                    section_id=section.id,
                    title=f"Risk in {section.title}: {marker}",
                    severity="high",
                    explanation=message,
                    location=f"section_{section.id}",
                    recommendation="Review and strengthen the relevant clause",
                    status="open",
                ))
        if sections and not section.content.strip():
            risks.append(RiskFinding(
                contract_id=contract_id,
                section_id=section.id,
                title=f"Section {section.title} is empty",
                severity="high",
                explanation="Empty sections cannot be safely exported",
                location=f"section_{section.id}",
                recommendation="Draft or remove the section before review",
                status="open",
            ))

    provider = MockLLMProvider()
    for finding in findings:
        review = await provider.review_draft({
            "validation_findings": [{"severity": finding.severity,
                                     "title": finding.title}],
            "risk_findings": [],
        })
        risks.append(RiskFinding(
            contract_id=contract_id,
            section_id=finding.section_id,
            title=finding.title,
            severity=finding.severity,
            explanation=finding.explanation,
            location=finding.location,
            recommendation=finding.recommendation or "Resolve before approval",
            status="open",
        ))

    for risk in risks:
        session.add(risk)
    session.commit()

    record_audit(session, "risk_analysis", user_id=user.id, contract_id=contract_id,
                 risk_count=len(risks))
    return {
        "contract_id": contract_id,
        "risk_count": len(risks),
        "severity_summary": {
            "blocker": sum(1 for r in risks if r.severity == "blocker"),
            "high": sum(1 for r in risks if r.severity == "high"),
            "warning": sum(1 for r in risks if r.severity == "warning"),
        },
        "requires_human_review": any(
            r.severity in ("blocker", "high") for r in risks),
    }