from typing import List, Optional, Dict, Any
from datetime import datetime
import re

from sqlmodel import Session, select

from apps.api.app.modules.core.models import (
    Contract, ContractSection, Clause, LegalSource, ValidationFinding, ValidationRun
)


# Deterministic validation rules
DETERMINISTIC_RULES = {
    "currency.consistent": {
        "type": "consistency",
        "severity": "blocker",
        "applies_to": ["service_agreement", "nda"],
        "check": lambda contract: _check_currency_consistency(contract),
    },
    "date.validity": {
        "type": "structure",
        "severity": "high",
        "applies_to": ["service_agreement"],
        "check": lambda contract: _check_date_validity(contract),
    },
    "required.fields": {
        "type": "input",
        "severity": "blocker",
        "applies_to": ["service_agreement", "nda"],
        "check": lambda contract: _check_required_fields(contract),
    },
    "clause.approved": {
        "type": "evidence",
        "severity": "high",
        "applies_to": ["service_agreement"],
        "check": lambda contract: _check_approved_clauses(contract),
    },
    "placeholder.check": {
        "type": "evidence",
        "severity": "blocker",
        "applies_to": ["service_agreement", "nda"],
        "check": lambda contract: _check_placeholders(contract),
    },
    "pack.match": {
        "type": "source_applicability",
        "severity": "blocker",
        "applies_to": ["*"],
        "check": lambda contract: _check_pack_match(contract),
    },
    "clause.status": {
        "type": "evidence",
        "severity": "high",
        "applies_to": ["service_agreement", "nda"],
        "check": lambda contract: _check_clause_status(contract),
    },
    "source.status": {
        "type": "source_applicability",
        "severity": "high",
        "applies_to": ["service_agreement", "nda"],
        "check": lambda contract: _check_source_status(contract),
    },
    "approval.status": {
        "type": "export",
        "severity": "blocker",
        "applies_to": ["service_agreement", "nda"],
        "check": lambda contract: _check_approval_soundness(contract),
    },
}

PLACEHOLDER_PATTERN = re.compile(r"(\[.*?\]|\{.*?\})")

REQUIRED_SECTIONS = ["Parties", "Payment", "Termination", "Governing Law"]

_CURRENCY_TOKENS = {
    "MAD": "MAD", "DH": "MAD",
    "TND": "TND", "DT": "TND",
    "USD": "USD", "$": "USD",
    "EUR": "EUR", "€": "EUR",
    "GBP": "GBP",
}


def _contract_text(contract: Contract) -> str:
    parts = [contract.name or "", contract.description or ""]
    for section in contract.sections:
        parts.append(section.title)
        parts.append(section.content)
    return "\n".join(parts)


def _check_currency_consistency(contract) -> List[ValidationFinding]:
    """Flag when the contract mixes more than one currency."""
    text = _contract_text(contract).upper()
    found = set()
    for token, canonical in _CURRENCY_TOKENS.items():
        if token in ("$", "€"):
            if token in text:
                found.add(canonical)
        elif re.search(rf"\b{re.escape(token)}\b", text):
            found.add(canonical)

    if len(found) > 1:
        return [ValidationFinding(
            rule_id="currency.consistent",
            severity="blocker",
            title="Currency inconsistency detected",
            explanation=f"Multiple currencies referenced: {', '.join(sorted(found))}",
            location="commercial_terms",
            recommendation="Select a single currency for all financial obligations",
            status="open",
        )]
    return []


def _parse_date(value: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def _check_date_validity(contract) -> List[ValidationFinding]:
    """Flag unparseable or out-of-order dates found in the contract facts."""
    findings: List[ValidationFinding] = []
    facts: Dict[str, Any] = getattr(contract, "facts", None) or {}

    parsed: List[tuple] = []
    for key, value in facts.items():
        if "date" not in key.lower():
            continue
        dt = _parse_date(str(value))
        if dt is None:
            findings.append(ValidationFinding(
                rule_id="date.validity",
                severity="high",
                title=f"Unparseable date in fact '{key}'",
                explanation=f"Value '{value}' is not a recognized date format (YYYY-MM-DD or DD/MM/YYYY)",
                location=f"facts.{key}",
                recommendation="Provide dates in a supported format",
                status="open",
            ))
        else:
            parsed.append((key, dt))

    if len(parsed) >= 2:
        parsed.sort(key=lambda kv: kv[1])
        start_key, _ = parsed[0]
        end_key, end_dt = parsed[-1]
        if end_dt < parsed[0][1]:
            findings.append(ValidationFinding(
                rule_id="date.validity",
                severity="high",
                title="End date precedes start date",
                explanation=f"Fact '{end_key}' is earlier than '{start_key}'",
                location="commercial_terms",
                recommendation="Ensure termination dates follow effective dates",
                status="open",
            ))
    return findings


def _check_required_fields(contract) -> List[ValidationFinding]:
    """Flag missing contract or missing required sections."""
    sections = contract.sections
    if not sections:
        return [ValidationFinding(
            rule_id="required.fields",
            severity="blocker",
            title="Missing required sections",
            explanation="Contract has no sections defined",
            location="structure",
            recommendation="Add required sections: " + ", ".join(REQUIRED_SECTIONS),
            status="open",
        )]

    titles = {s.title.lower() for s in sections}
    missing = [
        t for t in REQUIRED_SECTIONS
        if not any(req in title for title in titles for req in (t.lower(),))
    ]
    if missing:
        return [ValidationFinding(
            rule_id="required.fields",
            severity="blocker",
            title="Missing required sections",
            explanation=f"Contract is missing sections: {', '.join(missing)}",
            location="structure",
            recommendation="Add required sections: " + ", ".join(REQUIRED_SECTIONS),
            status="open",
        )]
    return []


def _check_approved_clauses(contract) -> List[ValidationFinding]:
    """Flag sections that have no approved clause assigned."""
    findings: List[ValidationFinding] = []
    for section in contract.sections:
        if not section.clause_ids:
            findings.append(ValidationFinding(
                rule_id="clause.approved",
                severity="high",
                title=f"No approved clause in {section.title}",
                explanation=f"Section '{section.title}' has no approved clause assigned",
                location=f"section_{section.id}",
                recommendation="Select an approved clause from the clause library",
                status="open",
            ))
    return findings


def _check_placeholders(contract) -> List[ValidationFinding]:
    """Flag unresolved placeholders ([] or {}) in any section."""
    findings: List[ValidationFinding] = []
    for section in contract.sections:
        if not section.content:
            continue
        matches = PLACEHOLDER_PATTERN.findall(section.content)
        if matches:
            findings.append(ValidationFinding(
                rule_id="placeholder.check",
                severity="blocker",
                title=f"Unresolved placeholder in {section.title}",
                explanation=f"Section '{section.title}' contains unresolved "
                            f"placeholder(s): {', '.join(dict.fromkeys(matches))}",
                location=f"section_{section.id}",
                recommendation="Replace placeholders with concrete values or "
                               "mark the section for human review",
                status="open",
            ))
    return findings


def _check_pack_match(contract) -> List[ValidationFinding]:
    """Flag when no active pack supports this contract type/jurisdiction."""
    from apps.api.app.modules.contracts.service import find_active_pack_and_type
    if not hasattr(contract, "id"):
        return []
    from sqlmodel import Session as _Session
    # reshaped check: relies on a matching active pack
    session = contract._session  # set by run_deterministic_validation  # pylint: disable=protected-access
    found = find_active_pack_and_type(session, contract.contract_type,
                                      contract.jurisdiction)
    if found is not None:
        return []
    return [ValidationFinding(
        rule_id="pack.match",
        severity="blocker",
        title="No active pack matches this contract",
        explanation=f"No active legal pack for type '{contract.contract_type}' "
                    f"and jurisdiction '{contract.jurisdiction}'",
        location="structure",
        recommendation="Activate a matching jurisdiction pack before drafting",
        status="open",
    )]


def _check_clause_status(contract) -> List[ValidationFinding]:
    """Flag section clause refs that are not approved."""
    session = contract._session  # pylint: disable=protected-access
    findings: List[ValidationFinding] = []
    for section in contract.sections:
        for cid in section.clause_ids:
            clause = session.get(Clause, cid) if cid else None
            if clause is None or clause.status != "approved":
                findings.append(ValidationFinding(
                    rule_id="clause.status",
                    severity="high",
                    title=f"Non-approved clause in {section.title}",
                    explanation=f"Section '{section.title}' references clause "
                                f"#{cid} which is not approved",
                    location=f"section_{section.id}",
                    recommendation="Use only approved clauses from the library",
                    status="open",
                ))
    return findings


def _check_source_status(contract) -> List[ValidationFinding]:
    """Flag evidence ids that do not resolve to approved + effective sources."""
    session = contract._session  # pylint: disable=protected-access
    findings: List[ValidationFinding] = []
    for section in contract.sections:
        for eid in section.evidence_ids:
            if not str(eid).isdigit():
                continue
            source = session.get(LegalSource, int(eid))
            if source is None or source.status != "approved":
                findings.append(ValidationFinding(
                    rule_id="source.status",
                    severity="high",
                    title=f"Unresolved source in {section.title}",
                    explanation=f"Evidence id '{eid}' in section '{section.title}' "
                                f"does not reference an approved source",
                    location=f"section_{section.id}",
                    recommendation="Re-retrieve evidence from approved sources",
                    status="open",
                ))
    return findings


def _check_approval_soundness(contract) -> List[ValidationFinding]:
    """Flag a contract that is approved/exported while blockers are open.

    Only real validation blockers count; approval/export bookkeeping findings
    are excluded to avoid self-reproduction across runs.
    """
    if contract.status not in ("approved", "exported"):
        return []
    open_blockers = [
        f for f in contract.validation_findings
        if f.severity == "blocker" and f.status == "open"
        and f.rule_id not in ("approval.status", "export.rule")
    ]
    if open_blockers:
        return [ValidationFinding(
            rule_id="approval.status",
            severity="blocker",
            title="Approved contract has open blockers",
            explanation=f"Contract is '{contract.status}' but {len(open_blockers)} "
                        f"blocker finding(s) are still open",
            location="approval",
            recommendation="Resolve all blockers, then re-validate",
            status="open",
        )]
    return []


def run_deterministic_validation(
    session: Session,
    contract_id: int,
) -> List[ValidationFinding]:
    """Run all deterministic validation rules applicable to a contract."""
    contract = session.get(Contract, contract_id)
    if not contract:
        return [ValidationFinding(
            rule_id="required.fields",
            severity="blocker",
            title="Contract not found",
            explanation=f"Contract {contract_id} does not exist",
            location="structure",
            recommendation="Create the contract before validating",
            status="open",
        )]

    setattr(contract, "_session", session)  # expose session to pure check helpers
    findings: List[ValidationFinding] = []
    for rule_id, rule in DETERMINISTIC_RULES.items():
        if "*" not in rule["applies_to"] and contract.contract_type not in rule["applies_to"]:
            continue
        for finding in rule["check"](contract):
            finding.contract_id = contract_id
            findings.append(finding)
    return findings


def open_blockers(session: Session, contract_id: int) -> List[ValidationFinding]:
    """All currently-open blocker findings for a contract."""
    return list(session.exec(select(ValidationFinding).where(
        (ValidationFinding.contract_id == contract_id) &
        (ValidationFinding.severity == "blocker") &
        (ValidationFinding.status == "open")
    )).all())


def run_validation(
    session: Session,
    contract_id: int,
    include_ai: bool = False,
    run_by: int = 1,
) -> Dict[str, Any]:
    """Run validation on a contract and return a summary."""

    contract = session.get(Contract, contract_id)
    if not contract:
        return {
            "status": "failed",
            "findings_count": 0,
            "blockers": 0,
            "high_risks": 0,
            "warnings": 0,
            "findings": [],
            "message": f"Contract {contract_id} not found",
        }

    findings = run_deterministic_validation(session, contract_id)
    blockers = sum(1 for f in findings if f.severity == "blocker")
    high_risks = sum(1 for f in findings if f.severity == "high")
    warnings = sum(1 for f in findings if f.severity == "warning")

    # Supersede open findings from previous runs (after new rules were assessed)
    for old in session.exec(select(ValidationFinding).where(
            ValidationFinding.contract_id == contract_id,
            ValidationFinding.status == "open")).all():
        old.status = "closed"
        session.add(old)
    session.commit()

    if blockers and contract.status not in ("approved", "exported"):
        findings.append(ValidationFinding(
            rule_id="export.rule",
            severity="blocker",
            title="Open blockers would block export",
            explanation=f"{blockers} blocker finding(s) must be resolved "
                        f"before final export",
            location="export",
            recommendation="Resolve blockers before requesting export",
            status="open",
        ))

    for finding in findings:
        session.add(finding)
    session.flush()

    def _to_dict(f):
        return {
            "id": getattr(f, "id", None),
            "rule_id": f.rule_id,
            "severity": f.severity,
            "title": f.title,
            "explanation": f.explanation,
            "location": f.location,
            "recommendation": f.recommendation,
            "status": f.status,
        }

    finding_dicts = [_to_dict(f) for f in findings]

    run = ValidationRun(
        contract_id=contract_id,
        run_by=run_by,
        status="completed",
        findings_count=len(findings),
        blockers=sum(1 for f in findings if f.severity == "blocker"),
        high_risks=sum(1 for f in findings if f.severity == "high"),
        warnings=sum(1 for f in findings if f.severity == "warning"),
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    session.add(run)
    session.commit()

    return {
        "status": "completed",
        "findings_count": len(findings),
        "blockers": blockers,
        "high_risks": high_risks,
        "warnings": warnings,
        "findings": finding_dicts,
    }
