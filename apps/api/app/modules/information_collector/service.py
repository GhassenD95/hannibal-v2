from typing import Optional, List, Dict, Any
from datetime import datetime
import re

from sqlmodel import Session, select

from apps.api.app.modules.core.models import (
    ContractRequest, CollectionStep, CollectionProgress
)
from apps.api.app.modules.information_collector.schemas import FieldValidation


def normalize_contract_type(raw_type: str) -> str:
    """Normalize contract type name to standard form."""
    mapping = {
        "nda": "nda",
        "non-disclosure agreement": "nda",
        "service agreement": "service_agreement",
        "service contract": "service_agreement",
        "sa": "service_agreement",
    }
    return mapping.get(raw_type.lower(), raw_type)


def normalize_jurisdiction(raw_jur: str) -> str:
    """Normalize jurisdiction name."""
    mapping = {
        "ma": "MA",
        "morocco": "MA",
        "tunisia": "TN",
        "tunisie": "TN",
        "tn": "TN",
        "france": "FR",
        "united states": "US",
        "usa": "US",
    }
    return mapping.get(raw_jur.lower(), raw_jur)


def collect_from_natural_language(
    description: str,
    user_id: int,
    db: Session
) -> ContractRequest:
    """Extract initial contract request from natural language description."""
    desc_lower = description.lower()

    contract_type = "service_agreement"  # default
    jurisdiction = "MA"  # default

    if "nda" in desc_lower or "non-disclosure" in desc_lower:
        contract_type = "nda"
    elif "service" in desc_lower or "agreement" in desc_lower:
        contract_type = "service_agreement"

    if "maroc" in desc_lower or "morocco" in desc_lower:
        jurisdiction = "MA"
    elif "tunisie" in desc_lower or "tunisia" in desc_lower:
        jurisdiction = "TN"
    elif "france" in desc_lower:
        jurisdiction = "FR"

    facts: Dict[str, str] = {}

    duration_match = re.search(r'(\d+)\s*(?:month|an|year)', desc_lower)
    if duration_match:
        amount = duration_match.group(1)
        unit = "months" if "month" in desc_lower else "years"
        facts["duration"] = f"{amount} {unit}"

    amount_match = re.search(r'(\d[\d\s.,]*)\s*(?:mad|dh|dollar|tnd|dt|dinar|€|\$)', desc_lower)
    if amount_match:
        facts["amount"] = amount_match.group(1).strip()

    party_patterns = re.findall(r'(?:between|for)\s+([A-Z][a-zA-Z\s]+?)(?:and|$)', description)
    if party_patterns:
        facts["parties"] = party_patterns[0].strip()

    request = ContractRequest(
        name=description[:50] + ("..." if len(description) > 50 else ""),
        description=description,
        contract_type=contract_type,
        jurisdiction=jurisdiction,
        facts=facts,
    )

    db.add(request)
    db.commit()
    db.refresh(request)

    step = CollectionStep(
        name="basics",
        order_index=1,
        is_complete=False,
        validation_issues=[],
        saved_state={"description": description},
    )
    db.add(step)

    progress = CollectionProgress(
        contract_request_id=request.id,
        step_name="basics",
        completed=False,
        field_count=3,
        required_count=3,
    )
    db.add(progress)
    db.commit()

    return request


def get_contract_request(db: Session, request_id: int) -> Optional[ContractRequest]:
    statement = select(ContractRequest).where(ContractRequest.id == request_id)
    result = db.exec(statement)
    return result.first()


def update_step_progress(
    db: Session,
    request_id: int,
    step_name: str,
    completed: bool,
    field_count: int,
    required_count: int
) -> CollectionProgress:
    """Update or create progress tracking for a collection step."""
    statement = select(CollectionProgress).where(
        CollectionProgress.contract_request_id == request_id,
        CollectionProgress.step_name == step_name
    )
    progress = db.exec(statement).first()

    if progress:
        progress.completed = completed
        progress.field_count = field_count
        progress.required_count = required_count
        progress.last_updated = datetime.utcnow()
    else:
        progress = CollectionProgress(
            contract_request_id=request_id,
            step_name=step_name,
            completed=completed,
            field_count=field_count,
            required_count=required_count,
        )
        db.add(progress)

    db.commit()
    db.refresh(progress)
    return progress


def validate_field(
    db: Session,
    request_id: Optional[int],
    field_name: str,
    field_value: Any
) -> Optional[FieldValidation]:
    """Validate a single field and return validation result if there's an issue."""
    if field_value is None or field_value == "":
        if field_name in ["contract_type", "jurisdiction"]:
            return FieldValidation(
                field_name=field_name,
                error_message=f"{field_name} is required",
                severity="blocker",
            )

    if field_name == "amount" and field_value:
        if not re.search(r'\d', str(field_value)):
            return FieldValidation(
                field_name=field_name,
                error_message="Amount must contain a number",
                severity="error",
            )

    if field_name == "duration" and field_value:
        if "month" not in str(field_value).lower() and "year" not in str(field_value).lower():
            return FieldValidation(
                field_name=field_name,
                error_message="Duration should specify month or year",
                severity="warning",
            )

    return None
