"""Evaluation engine: drives the pipeline against fixtures and computes
metrics documented in docs/12-evaluation.md."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from sqlmodel import Session, select

from apps.api.app.modules.core.models import (
    Users, EvaluationFixture, EvaluationRun, ContractSection,
    LegalSource,
)
from apps.api.app.modules.core.audit import record_audit
from apps.api.app.modules.contracts.service import (
    create_contract_request, confirm_request, interpret_request,
)
from apps.api.app.modules.generation.service import build_plan, generate_contract
from apps.api.app.modules.validation.service import run_validation
from apps.api.app.modules.rag.service import get_evidence_for_section

FIXTURES_PATH = Path(__file__).resolve().parents[5] / "tests" / "evaluation" / "fixtures.json"

# Keys documented in docs/12-evaluation.md (0.0 placeholder values are valid).
METRIC_SCHEMA = {
    "extraction": {
        "field_precision", "field_recall", "normalization_accuracy",
        "ambiguity_detection_accuracy",
    },
    "retrieval": {
        "recall_at_5", "precision_at_5", "mrr",
        "wrong_jurisdiction_leakage", "expired_source_retrieval_rate",
    },
    "planning": {
        "required_section_recall", "required_clause_recall",
        "irrelevant_clause_rate", "unresolved_decision_recall",
    },
    "generation": {
        "schema_validity", "factual_consistency", "evidence_coverage",
        "citation_validity", "unsupported_assertion_rate",
        "human_acceptance_rate",
    },
    "validation": {
        "precision", "recall", "false_positive_rate", "false_negative_rate",
    },
    "system": {
        "median_latency", "p95_latency", "cost_per_generation",
        "export_success_rate", "failure_recovery_rate",
    },
}


def load_fixtures() -> List[Dict[str, Any]]:
    fixtures = []
    if FIXTURES_PATH.exists():
        payload = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
        fixtures.extend(payload.get("fixtures", []))
    return fixtures


def load_fixtures_from_db(session: Session) -> List[Dict[str, Any]]:
    rows = session.exec(select(EvaluationFixture).where(
        EvaluationFixture.source == "db")).all()
    return [
        {
            "id": row.fixture_id,
            "name": row.name,
            "jurisdiction": row.jurisdiction,
            "contractType": row.contract_type,
            "input": row.input,
            "expectedSections": row.expected_sections,
            "requiredClauses": row.required_clauses,
            "expectedEvidence": row.expected_evidence,
            "expectedRisks": row.expected_risks,
            "forbiddenClaims": row.forbidden_claims,
        }
        for row in rows
    ]


def all_fixtures(session: Session) -> List[Dict[str, Any]]:
    return load_fixtures() + load_fixtures_from_db(session)


def detect_forbidden_claims(text: str, forbidden_claims: List[str]) -> List[str]:
    """Return forbidden claims whose tokens appear in the given text."""
    lower = text.lower()
    hits = []
    for claim in forbidden_claims:
        tokens = [t.strip().rstrip(".") for t in claim.split() if len(t) > 3]
        if tokens and all(t.lower() in lower for t in tokens):
            hits.append(claim)
    return hits


def _metric_base() -> Dict[str, Any]:
    return {
        "extraction": {
            "field_precision": 0.0, "field_recall": 0.0,
            "normalization_accuracy": 0.0, "ambiguity_detection_accuracy": 0.0,
        },
        "retrieval": {
            "recall_at_5": 0.0, "precision_at_5": 0.0, "mrr": 0.0,
            "wrong_jurisdiction_leakage": 0.0,
            "expired_source_retrieval_rate": 0.0,
        },
        "planning": {
            "required_section_recall": 0.0, "required_clause_recall": 0.0,
            "irrelevant_clause_rate": 0.0, "unresolved_decision_recall": 0.0,
        },
        "generation": {
            "schema_validity": 0.0, "factual_consistency": 0.0,
            "evidence_coverage": 0.0, "citation_validity": 0.0,
            "unsupported_assertion_rate": 0.0, "human_acceptance_rate": 0.0,
        },
        "validation": {
            "precision": 0.0, "recall": 0.0,
            "false_positive_rate": 0.0, "false_negative_rate": 0.0,
        },
        "system": {
            "median_latency": 0.0, "p95_latency": 0.0,
            "cost_per_generation": 0.0, "export_success_rate": 0.0,
            "failure_recovery_rate": 0.0,
        },
    }


async def evaluate_fixture(session: Session, user: Users,
                           fixture: Dict[str, Any]) -> Dict[str, Any]:
    """Run one fixture through the pipeline and compute its metrics."""
    metrics = _metric_base()
    fixture_id = fixture.get("id", "unknown")
    description = (fixture.get("input") or {}).get("description", "")

    request = create_contract_request(session, user, {
        "name": fixture.get("name", fixture_id),
        "description": description,
        "contract_type": fixture.get("contractType", "service_agreement"),
        "jurisdiction": fixture.get("jurisdiction", "MA"),
    })
    interpret_request(session, user, request.id, description)
    contract = confirm_request(session, user, request.id)

    plan = build_plan(session, user, contract.id)
    generation = await generate_contract(session, user, contract.id)
    validation = run_validation(session, contract.id, run_by=user.id)
    sections = list(session.exec(select(ContractSection).where(
        ContractSection.contract_id == contract.id).order_by(
        ContractSection.order_index)).all())

    expected_sections = {s.lower() for s in fixture.get("expectedSections", [])}
    plan_sections = {s.lower() for s in plan.sections_required}
    if expected_sections:
        metrics["planning"]["required_section_recall"] = round(
            len(plan_sections & expected_sections) / len(expected_sections), 4)

    statuses = {s.status for s in sections}
    valid_statuses = {"supported", "needs_review", "unsupported", "approved"}
    schema_valid = (len(sections) > 0 and statuses.issubset(valid_statuses)
                    and all(s.content.strip() for s in sections))
    metrics["generation"]["schema_validity"] = 1.0 if schema_valid else 0.0

    sensitive = [s for s in sections]
    covered = [s for s in sensitive if s.evidence_ids]
    if sensitive:
        metrics["generation"]["evidence_coverage"] = round(
            len(covered) / len(sensitive), 4)

    unsupported = [s for s in sections if s.status == "unsupported"]
    if sections:
        metrics["generation"]["unsupported_assertion_rate"] = round(
            len(unsupported) / len(sections), 4)

    citations = [eid for s in sections for eid in s.evidence_ids]
    if citations:
        known_ids = {str(src.id) for src in session.exec(select(LegalSource)).all()}
        valid_cites = [eid for eid in citations if eid in known_ids]
        metrics["generation"]["citation_validity"] = round(
            len(valid_cites) / len(citations), 4)

    # Retrieval surface: evidence per legal-sensitive section
    evidence_hits = 0
    leakage = 0
    expired = 0
    retrieved = 0
    for section in sensitive:
        evidence = get_evidence_for_section(
            session, section.title, contract.jurisdiction,
            contract.contract_type, limit=5)
        if evidence:
            evidence_hits += 1
        for item in evidence:
            retrieved += 1
            if item.jurisdiction and item.jurisdiction != contract.jurisdiction:
                leakage += 1
            src = None
            try:
                src = session.get(LegalSource, int(item.source_id))
            except (TypeError, ValueError):
                src = None
            if src is None:
                expired += 1
            elif src.status != "approved" or (
                    src.effective_date is not None
                    and src.effective_date > datetime.utcnow()):
                expired += 1
    if sensitive:
        metrics["retrieval"]["recall_at_5"] = round(evidence_hits / len(sensitive), 4)
    if retrieved:
        metrics["retrieval"]["precision_at_5"] = round(evidence_hits / retrieved, 4)
        metrics["retrieval"]["wrong_jurisdiction_leakage"] = round(
            leakage / retrieved, 4)
        metrics["retrieval"]["expired_source_retrieval_rate"] = round(
            expired / retrieved, 4)

    # Validation precision/recall against expected risks (keyword overlap)
    expected_risks = [r.lower() for r in fixture.get("expectedRisks", [])]
    finding_text = " ".join(
        f"{f['title']} {f['explanation']}" if isinstance(f, dict)
        else f"{f.title} {f.explanation}"
        for f in validation["findings"]).lower()
    hits_fp = sum(1 for risk in expected_risks if risk.split()[0] in finding_text)
    metrics["validation"]["recall"] = round(
        hits_fp / len(expected_risks), 4) if expected_risks else 0.0
    tp = hits_fp
    fp = max(0, len(validation["findings"]) - tp)
    metrics["validation"]["precision"] = round(
        tp / (tp + fp), 4) if (tp + fp) else 0.0
    metrics["validation"]["false_positive_rate"] = round(
        fp / max(1, len(validation["findings"])), 4)
    metrics["validation"]["false_negative_rate"] = round(
        1.0 - metrics["validation"]["recall"], 4)

    # Forbidden-claim detection on input + generated content
    all_text = description + " " + json.dumps(
        {s.title: s.content for s in sections}, ensure_ascii=False)
    forbidden_hits = detect_forbidden_claims(
        all_text, fixture.get("forbiddenClaims", []))
    metrics["forbidden_claims_hit"] = 1 if forbidden_hits else 0

    metrics["fixture_id"] = fixture_id
    metrics["contract_id"] = contract.id
    metrics["status"] = generation.get("status", "unknown")
    return metrics


async def run_evaluation(session: Session, user: Users) -> Dict[str, Any]:
    fixtures = all_fixtures(session)
    per_fixture = []
    for fixture in fixtures:
        per_fixture.append(await evaluate_fixture(session, user, fixture))

    if per_fixture:
        metrics = aggregate(per_fixture)
    else:
        metrics = _metric_base()

    run = EvaluationRun(
        run_by=user.id,
        status="completed",
        total_fixtures=len(per_fixture),
        metrics=metrics,
        per_fixture=per_fixture,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    record_audit(session, "evaluation_run", user_id=user.id,
                 run_id=run.id, total_fixtures=len(per_fixture))
    return {"run_id": run.id, "metrics": metrics, "per_fixture": per_fixture}


def aggregate(per_fixture: List[Dict[str, Any]]) -> Dict[str, Any]:
    agg = _metric_base()
    forbidden_hits = sum(f.get("forbidden_claims_hit", 0) for f in per_fixture)
    agg["forbidden_claims_hit_rate"] = round(
        forbidden_hits / len(per_fixture), 4) if per_fixture else 0.0
    for category, keys in METRIC_SCHEMA.items():
        for key in keys:
            values = [f.get(category, {}).get(key) for f in per_fixture]
            values = [v for v in values if isinstance(v, (int, float))]
            agg[category][key] = round(
                sum(values) / len(values), 4) if values else 0.0
    return agg