"""Shared audit event recording."""

from typing import Any, Dict, Optional

from sqlmodel import Session

from apps.api.app.modules.core.models import AuditEvent


def record_audit(
    session: Session,
    event_type: str,
    user_id: int = 0,
    contract_id: Optional[int] = None,
    **data: Any,
) -> AuditEvent:
    """Append an audit event. Never logs full contract content."""
    event = AuditEvent(
        event_type=event_type,
        contract_id=contract_id,
        user_id=user_id,
        event_data={key: value for key, value in data.items()},
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event