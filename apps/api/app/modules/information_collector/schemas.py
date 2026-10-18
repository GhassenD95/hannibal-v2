from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field


class FieldValidation(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    field_name: str
    error_message: str
    severity: str  # info, warning, error, blocker


class ExtractRequest(SQLModel):
    """Body for POST /information-collector/extract."""
    description: str
    contract_type: Optional[str] = None
    jurisdiction: Optional[str] = None
    user_id: int = 1


class ValidateFieldRequest(SQLModel):
    """Body for POST /information-collector/validate/{field_name}."""
    field_name: str
    field_value: str


class ProgressUpdateRequest(SQLModel):
    """Body for POST /information-collector/{request_id}/progress/{step_name}."""
    completed: bool
    field_count: int = 0
    required_count: int = 0
